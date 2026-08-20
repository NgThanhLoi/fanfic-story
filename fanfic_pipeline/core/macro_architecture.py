"""
Macro-Architecture Engine for 100-1000+ Chapters Long-form Fanfic.
Implements:
1. Hierarchical Plot Tree (Macro Arc -> Meso Volume -> Micro Chapter -> Scene Beat)
2. Epistemic Ledger (Information Boundary & Who Knows What)
3. Foreshadowing & Chekhov's Gun Lifecycle Manager
4. Off-Screen World Evolution Simulator
5. v1.1: BeatContract, NarrativeDebt, NarrativeDebtLedger (branch-aware)
"""

from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field
import json
import os
import hashlib
import datetime


# ------------------------------------------------------------------
# Existing v0.8 models (kept backward compat)
# ------------------------------------------------------------------
class ForeshadowingHook(BaseModel):
    hook_id: str
    description: str
    planted_chapter: int
    target_harvest_chapter: int
    urgency: Literal["low", "medium", "high", "critical"]
    status: Literal["planted", "ripening", "harvested", "abandoned"]
    involved_characters: List[str]
    notes: Optional[str] = ""


class EpistemicBoundary(BaseModel):
    character_name: str
    known_facts: List[str] = Field(description="Những gì nhân vật biết chắc chắn")
    false_beliefs: List[str] = Field(description="Những hiểu lầm / thông tin sai lệch nhân vật đang tin")
    forbidden_knowledge: List[str] = Field(description="Những bí mật vũ trụ nhân vật TUYỆT ĐỐI CHƯA ĐƯỢC BIẾT (tránh AI toàn tri)")


class VolumeArc(BaseModel):
    volume_number: int
    title: str
    start_chapter: int
    end_chapter: int
    core_theme: str
    main_antagonist_or_force: str
    realm_milestone: str = Field(description="Mốc cảnh giới mục tiêu của nhân vật chính trong Quyển này")
    cp_milestone: str = Field(description="Bước chuyển biến quan hệ tình cảm trong Quyển này")
    major_turning_points: List[str] = Field(description="Các đại biến cố mấu chốt")




# ------------------------------------------------------------------
# v1.1: BeatContract — closed vocabulary preconditions
# ------------------------------------------------------------------
CLOSED_PRECONDITION_PREFIXES = ("realm>=", "realm==", "owns:", "knows:", "location:", "has_status:", "faction:", "deadline<=", "chapter>=")

class BeatContract(BaseModel):
    """Single chapter intent with enforceable pre/post conditions."""
    beat_id: str = Field(description="e.g. beat_001_ch12")
    plan_id: str = Field(description="parent plan/arc id")
    chapter_target: Optional[int] = Field(default=None, description="intended chapter number")
    title: str = Field(default="", description="short intent title")
    preconditions: List[str] = Field(default_factory=list, description="closed vocabulary: realm>=..., owns:..., knows:..., location:..., etc")
    postconditions: List[str] = Field(default_factory=list, description="what must be true after chapter")
    allowed_reveals: List[str] = Field(default_factory=list, description="facts permitted to be revealed in this beat")
    risk_hints: List[str] = Field(default_factory=list, description="narrative risks if beat is mishandled")
    summary: str = Field(default="", description="one-line beat summary for writer")

    def validate_preconditions_vocab(self) -> List[str]:
        """Return list of invalid precondition strings (closed vocab check)."""
        invalid = []
        for p in self.preconditions:
            if not any(p.startswith(prefix) for prefix in CLOSED_PRECONDITION_PREFIXES):
                # also allow plain "hook:" and "debt:" for ledger linking
                if not (p.startswith("hook:") or p.startswith("debt:")):
                    invalid.append(p)
        return invalid

    def check_against_state(self, state: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Simplified state check: ensures preconditions not obviously violated."""
        # This is a lightweight heuristic; real check would parse realm ordering
        failures = []
        loc = state.get("current_location", "")
        inventories = state.get("character_inventories", {})
        for p in self.preconditions:
            if p.startswith("location:"):
                expected = p.split(":", 1)[1]
                if expected and expected not in loc:
                    # not a hard failure, just hint
                    pass
            elif p.startswith("owns:"):
                # owns:Character:Item
                try:
                    _, char, item = p.split(":", 2)
                except ValueError:
                    try:
                        _, item = p.split(":", 1)
                        char = ""
                    except ValueError:
                        continue
                if char and char in inventories and item not in inventories[char]:
                    failures.append(f"Missing ownership {p}")
        return len(failures) == 0, failures


# ------------------------------------------------------------------
# v1.1: Narrative Debt
# ------------------------------------------------------------------
class NarrativeDebt(BaseModel):
    debt_id: str
    branch_id: str = "main"
    type: Literal["hook", "promise", "mystery", "relationship", "goal", "resource"] = "hook"
    description: str = ""
    created_chapter: int
    last_touched: int = Field(description="last chapter where debt was referenced")
    deadline_chapter: Optional[int] = Field(default=None, description="must be resolved by this chapter")
    importance: int = Field(default=5, ge=1, le=10)
    depends_on: List[str] = Field(default_factory=list, description="debt_ids this depends on")
    status: Literal["active", "resolved", "stale", "abandoned"] = "active"
    evidence_spans: List[str] = Field(default_factory=list, description="text evidence references")


class NarrativeDebtLedger:
    """Branch-aware ledger tracking unresolved narrative debts."""
    def __init__(self, branch_id: str = "main"):
        self.branch_id = branch_id
        self.debts: Dict[str, NarrativeDebt] = {}

    def add_debt(self, debt: NarrativeDebt) -> NarrativeDebt:
        if debt.branch_id != self.branch_id:
            # allow cross-branch but normalize
            debt.branch_id = self.branch_id
        if debt.debt_id in self.debts:
            raise ValueError(f"Debt {debt.debt_id} already exists on branch {self.branch_id}")
        self.debts[debt.debt_id] = debt
        return debt

    def touch_debt(self, debt_id: str, chapter_num: int, evidence: Optional[str] = None):
        if debt_id not in self.debts:
            raise KeyError(f"Debt {debt_id} not found")
        d = self.debts[debt_id]
        d.last_touched = chapter_num
        if evidence:
            d.evidence_spans.append(evidence)
        if d.status == "stale":
            d.status = "active"

    def resolve_debt(self, debt_id: str, chapter_num: int):
        if debt_id not in self.debts:
            raise KeyError(f"Debt {debt_id} not found")
        d = self.debts[debt_id]
        d.status = "resolved"
        d.last_touched = chapter_num

    def abandon_debt(self, debt_id: str):
        if debt_id in self.debts:
            self.debts[debt_id].status = "abandoned"

    def get_stale_debts(self, current_chapter: int, stale_threshold: int = 15) -> List[NarrativeDebt]:
        """Debts not touched for stale_threshold chapters."""
        out = []
        for d in self.debts.values():
            if d.status != "active":
                continue
            if current_chapter - d.last_touched >= stale_threshold:
                # mark stale lazily
                d.status = "stale"
                out.append(d)
            elif d.status == "stale":
                out.append(d)
        return out

    def get_due_debts(self, current_chapter: int, horizon: int = 3) -> List[NarrativeDebt]:
        """Debts whose deadline is within horizon chapters."""
        out = []
        for d in self.debts.values():
            if d.status not in ("active", "stale"):
                continue
            if d.deadline_chapter is not None and d.deadline_chapter <= current_chapter + horizon:
                out.append(d)
        # sort by deadline then importance
        out.sort(key=lambda x: (x.deadline_chapter or 9999, -x.importance))
        return out

    def get_active_debts(self) -> List[NarrativeDebt]:
        return [d for d in self.debts.values() if d.status == "active"]

    def debt_pressure(self, current_chapter: int) -> List[NarrativeDebt]:
        """Combined pressure: due + stale sorted by importance."""
        due = self.get_due_debts(current_chapter, horizon=5)
        stale = self.get_stale_debts(current_chapter)
        # merge unique
        seen = set()
        merged = []
        for d in due + stale:
            if d.debt_id not in seen:
                merged.append(d)
                seen.add(d.debt_id)
        # add remaining active high importance
        for d in sorted(self.get_active_debts(), key=lambda x: -x.importance):
            if d.debt_id not in seen and d.importance >= 8:
                merged.append(d)
                seen.add(d.debt_id)
        return merged

    def to_list(self) -> List[Dict[str, Any]]:
        return [d.model_dump() for d in self.debts.values()]

    def load_from_list(self, data: List[Dict[str, Any]]):
        for item in data:
            d = NarrativeDebt(**item)
            self.debts[d.debt_id] = d


# ------------------------------------------------------------------
# Existing MacroStoryBible kept, extended with ledger accessor
# ------------------------------------------------------------------
class MacroStoryBible(BaseModel):
    fandom: str
    total_planned_volumes: int
    volumes: List[VolumeArc]
    active_foreshadowings: List[ForeshadowingHook]
    epistemic_boundaries: Dict[str, EpistemicBoundary]
    world_timeline_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Các sự kiện thế lực hậu trường (Ma Môn, Thiếu Lâm, Lục Đạo) diễn ra off-screen"
    )

    def get_current_volume(self, chapter_num: int) -> Optional[VolumeArc]:
        for v in self.volumes:
            if v.start_chapter <= chapter_num <= v.end_chapter:
                return v
        return self.volumes[-1] if self.volumes else None

    def get_due_foreshadowings(self, current_chapter: int) -> List[ForeshadowingHook]:
        return [
            h for h in self.active_foreshadowings 
            if h.status in ["planted", "ripening"] and h.target_harvest_chapter <= current_chapter + 3
        ]

    def harvest_hook(self, hook_id: str, chapter_num: int):
        for h in self.active_foreshadowings:
            if h.hook_id == hook_id:
                h.status = "harvested"
                h.notes += f" | Đã thu hồi tại Chương {chapter_num}"
                break
