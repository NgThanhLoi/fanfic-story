"""
Hierarchical Story Planner v1.1 (FR-12, FR-14, FR-15 + Sealing/Rolling Horizon):
- Series -> Volume (100-250c) -> Arc (15-40c) -> Mini-Arc (4-10c) -> Chapter Plan
- Dynamic Foreshadowing Lifecycle
- Epistemic Boundary Enforcement
- v1.1: SealedArc, RollingPlan, arc sealing, horizon reconcile, debt pressure
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import hashlib
import datetime

from fanfic_pipeline.core.macro_architecture import ForeshadowingHook, EpistemicBoundary, VolumeArc, BeatContract, NarrativeDebt, NarrativeDebtLedger


class MiniArc(BaseModel):
    mini_arc_id: str
    title: str
    chapter_range: List[int]
    objective: str
    escalation_beat: str
    climax_payoff: str
    exit_criteria: str


class StoryArc(BaseModel):
    arc_id: str
    volume_number: int
    title: str
    start_chapter: int
    end_chapter: int
    arc_theme: str
    main_antagonist: str
    mini_arcs: List[MiniArc] = Field(default_factory=list)
    key_payoffs: List[str] = Field(default_factory=list)


class SealedArc(BaseModel):
    """Immutable sealed arc version for writer contract."""
    arc_id: str
    version: int = 1
    sealed_at_chapter: int
    sealed_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    plan_hash: str = Field(description="sha256[:16] of sealed content")
    is_sealed: bool = True
    chapter_intents: List[BeatContract] = Field(default_factory=list)

    def verify_hash(self, plan_hash: str) -> bool:
        return self.plan_hash == plan_hash


class RollingPlan(BaseModel):
    """Rolling horizon plan: next 3-8 chapter intents regenerated after each commit."""
    plan_id: str
    branch_id: str = "main"
    horizon_start: int
    horizon_end: int
    source_head_tx: str = Field(description="tx_id of head chapter this plan was derived from")
    version: int = 1
    chapter_intents: List[BeatContract] = Field(default_factory=list)
    debt_pressure: List[NarrativeDebt] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


    def reconcile_horizon(self, committed_chapter: int, new_head_tx: str, planner: "HierarchicalStoryPlanner") -> "RollingPlan":
        """
        Regenerate next 3-8 intents from committed prose/state + debt pressure.
        Produces a new RollingPlan version with updated horizon.
        """
        # compute new horizon: start = committed_chapter+1, end = start+5 (clamped 3-8)
        new_start = committed_chapter + 1
        # debt pressure influences horizon length: high pressure extends horizon
        current_chapter = committed_chapter
        pressure = []
        if planner.debt_ledger is not None:
            pressure = planner.debt_ledger.debt_pressure(current_chapter)
        # if many due debts, extend horizon to 8, else 5
        horizon_len = 8 if len(pressure) >= 3 else 5
        horizon_len = max(3, min(8, horizon_len))
        new_end = new_start + horizon_len - 1

        # generate new intents: one per chapter in horizon
        new_intents: List[BeatContract] = []
        for idx, ch in enumerate(range(new_start, new_end + 1)):
            # pick debt to weave in round-robin
            related_debt = pressure[idx % len(pressure)] if pressure else None
            preconds = []
            allowed = []
            risks = []
            if related_debt:
                preconds.append(f"debt:{related_debt.debt_id}")
                allowed.append(related_debt.description[:60])
                if related_debt.deadline_chapter and related_debt.deadline_chapter <= ch + 2:
                    risks.append(f"Debt {related_debt.debt_id} deadline approaching ch {related_debt.deadline_chapter}")
            # add generic realm precondition based on current volume
            vol = planner.get_current_volume(ch)
            if vol:
                preconds.append(f"chapter>={ch}")
            beat = BeatContract(
                beat_id=f"beat_{self.plan_id}_{ch:04d}",
                plan_id=self.plan_id,
                chapter_target=ch,
                title=f"Horizon intent ch {ch} — {related_debt.type if related_debt else 'advance'}",
                preconditions=preconds,
                postconditions=[f"progress for ch {ch}"],
                allowed_reveals=allowed,
                risk_hints=risks,
                summary=f"Rolling intent for ch {ch} derived from head {new_head_tx[:8] if new_head_tx else 'init'}",
            )
            new_intents.append(beat)

        return RollingPlan(
            plan_id=self.plan_id,
            branch_id=self.branch_id,
            horizon_start=new_start,
            horizon_end=new_end,
            source_head_tx=new_head_tx,
            version=self.version + 1,
            chapter_intents=new_intents,
            debt_pressure=pressure,
            created_at=datetime.datetime.utcnow().isoformat() + "Z",
        )


class HierarchicalStoryPlanner:
    def __init__(self, volumes: List[VolumeArc], arcs: List[StoryArc], hooks: List[ForeshadowingHook], epistemic: Dict[str, EpistemicBoundary], branch_id: str = "main"):
        self.volumes = volumes
        self.arcs = arcs
        self.hooks = hooks
        self.epistemic = epistemic
        self.branch_id = branch_id
        # v1.1: sealing registry & rolling plan & debt ledger
        self._sealed_arcs: Dict[str, SealedArc] = {}
        self._seal_versions: Dict[str, int] = {}
        self.rolling_plan: Optional[RollingPlan] = None
        self.debt_ledger = NarrativeDebtLedger(branch_id=branch_id)
        # seed ledger from hooks
        for h in self.hooks:
            try:
                self.debt_ledger.add_debt(NarrativeDebt(
                    debt_id=h.hook_id,
                    branch_id=branch_id,
                    type="hook",
                    description=h.description,
                    created_chapter=h.planted_chapter,
                    last_touched=h.planted_chapter,
                    deadline_chapter=h.target_harvest_chapter,
                    importance={"low": 3, "medium": 5, "high": 8, "critical": 10}.get(h.urgency, 5),
                    status="active" if h.status in ("planted", "ripening") else ("resolved" if h.status == "harvested" else "abandoned"),
                    evidence_spans=[],
                ))
            except Exception:
                pass
        # init rolling plan horizon from chapter 1
        self._init_rolling_plan()

    def _init_rolling_plan(self):
        # default horizon 1-5
        intents = []
        for ch in range(1, 6):
            intents.append(BeatContract(
                beat_id=f"beat_init_{ch:04d}",
                plan_id="main_plan",
                chapter_target=ch,
                title=f"Initial horizon ch {ch}",
                preconditions=[f"chapter>={ch}"],
                postconditions=[f"progress ch {ch}"],
                allowed_reveals=[],
                risk_hints=[],
                summary=f"Seed intent for ch {ch}",
            ))
        self.rolling_plan = RollingPlan(
            plan_id="main_plan",
            branch_id=self.branch_id,
            horizon_start=1,
            horizon_end=5,
            source_head_tx="genesis",
            version=1,
            chapter_intents=intents,
            debt_pressure=self.debt_ledger.debt_pressure(1),
        )

    # ---- existing getters ----
    def get_current_volume(self, chapter_num: int) -> Optional[VolumeArc]:
        for v in self.volumes:
            if v.start_chapter <= chapter_num <= v.end_chapter:
                return v
        return self.volumes[-1] if self.volumes else None

    def get_current_arc(self, chapter_num: int) -> Optional[StoryArc]:
        for a in self.arcs:
            if a.start_chapter <= chapter_num <= a.end_chapter:
                return a
        return None

    def get_current_mini_arc(self, chapter_num: int) -> Optional[MiniArc]:
        arc = self.get_current_arc(chapter_num)
        if not arc:
            return None
        for m in arc.mini_arcs:
            if m.chapter_range[0] <= chapter_num <= m.chapter_range[1]:
                return m
        return None

    def get_due_hooks(self, chapter_num: int) -> List[ForeshadowingHook]:
        return [
            h for h in self.hooks
            if h.status in ["planted", "ripening"] and h.target_harvest_chapter <= chapter_num + 3
        ]

    def get_epistemic_restrictions(self, pov_character: str) -> Optional[EpistemicBoundary]:
        for name, bound in self.epistemic.items():
            if name.lower() in pov_character.lower() or pov_character.lower() in name.lower():
                return bound
        return None

    def get_hierarchical_context(self, chapter_num: int, pov_character: str) -> Dict[str, Any]:
        vol = self.get_current_volume(chapter_num)
        arc = self.get_current_arc(chapter_num)
        mini = self.get_current_mini_arc(chapter_num)
        due_hooks = self.get_due_hooks(chapter_num)
        epistemic = self.get_epistemic_restrictions(pov_character)

        return {
            "volume_title": vol.title if vol else "Quyển 1",
            "volume_realm_milestone": vol.realm_milestone if vol else "",
            "volume_cp_milestone": vol.cp_milestone if vol else "",
            "arc_title": arc.title if arc else "Phân đoạn tân thủ",
            "arc_antagonist": arc.main_antagonist if arc else "Lục Đạo thử thách",
            "mini_arc_objective": mini.objective if mini else "Hoàn thành nhiệm vụ phân cảnh",
            "due_hooks": [f"[{h.hook_id}] {h.description} (Hạn ch.{h.target_harvest_chapter})" for h in due_hooks],
            "forbidden_knowledge": epistemic.forbidden_knowledge if epistemic else []
        }

    # ---- v1.1: Arc sealing ----
    def seal_current_arc(self, chapter_num: int) -> SealedArc:
        arc = self.get_current_arc(chapter_num)
        if not arc:
            raise ValueError(f"No arc found for chapter {chapter_num} to seal")
        # build chapter intents from arc mini-arcs + due hooks
        intents: List[BeatContract] = []
        for mini in arc.mini_arcs:
            # each mini yields 1-2 beats
            for beat_idx, ch in enumerate(range(mini.chapter_range[0], min(mini.chapter_range[1], mini.chapter_range[0] + 2) + 1)):
                intents.append(BeatContract(
                    beat_id=f"beat_{arc.arc_id}_{mini.mini_arc_id}_{beat_idx}",
                    plan_id=arc.arc_id,
                    chapter_target=ch,
                    title=mini.title,
                    preconditions=[f"chapter>={ch}"],
                    postconditions=[mini.exit_criteria],
                    allowed_reveals=[mini.objective[:80]],
                    risk_hints=[mini.escalation_beat[:80]] if mini.escalation_beat else [],
                    summary=mini.objective,
                ))
        # also add due hooks as beats
        for h in self.get_due_hooks(chapter_num):
            intents.append(BeatContract(
                beat_id=f"beat_{arc.arc_id}_hook_{h.hook_id}",
                plan_id=arc.arc_id,
                chapter_target=h.target_harvest_chapter,
                title=f"Harvest {h.hook_id}",
                preconditions=[f"hook:{h.hook_id}", f"chapter>={chapter_num}"],
                postconditions=[f"harvested:{h.hook_id}"],
                allowed_reveals=[h.description[:80]],
                risk_hints=[f"urgency:{h.urgency}"],
                summary=f"Hook harvest {h.hook_id}",
            ))

        # hash deterministically
        payload = {
            "arc_id": arc.arc_id,
            "mini_ids": [m.mini_arc_id for m in arc.mini_arcs],
            "intents": [b.model_dump() for b in intents],
        }
        plan_hash = hashlib.sha256(__import__("json").dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
        version = self._seal_versions.get(arc.arc_id, 0) + 1
        self._seal_versions[arc.arc_id] = version
        sealed = SealedArc(
            arc_id=arc.arc_id,
            version=version,
            sealed_at_chapter=chapter_num,
            plan_hash=plan_hash,
            is_sealed=True,
            chapter_intents=intents,
        )
        self._sealed_arcs[arc.arc_id] = sealed
        return sealed

    def get_sealed_arc(self, arc_id: str) -> Optional[SealedArc]:
        return self._sealed_arcs.get(arc_id)

    def verify_writer_plan_hash(self, arc_id: str, plan_hash: str) -> bool:
        """Writer only receives beats from sealed version; stale hash rejected."""
        sealed = self._sealed_arcs.get(arc_id)
        if not sealed:
            return False
        return sealed.plan_hash == plan_hash

    def get_writer_beats(self, chapter_num: int, plan_hash: Optional[str] = None) -> List[BeatContract]:
        """Return beats for chapter_num filtered; if plan_hash provided verify against sealed version."""
        arc = self.get_current_arc(chapter_num)
        if not arc:
            return []
        sealed = self._sealed_arcs.get(arc.arc_id)
        if sealed:
            if plan_hash is not None and sealed.plan_hash != plan_hash:
                raise ValueError(f"409 STALE_PLAN: sealed plan hash mismatch for arc {arc.arc_id}: expected {sealed.plan_hash}, got {plan_hash}")
            # return beats targeting this chapter
            return [b for b in sealed.chapter_intents if b.chapter_target == chapter_num]
        # not sealed yet: return empty or fallback to rolling plan
        if self.rolling_plan:
            return [b for b in self.rolling_plan.chapter_intents if b.chapter_target == chapter_num]
        return []

    def reconcile_horizon(self, committed_chapter: int, new_head_tx: str):
        """Delegate to RollingPlan.reconcile_horizon."""
        if self.rolling_plan is None:
            self._init_rolling_plan()
        self.rolling_plan = self.rolling_plan.reconcile_horizon(committed_chapter, new_head_tx, self)
        return self.rolling_plan
