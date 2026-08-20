"""
P2.5 — Divergence Ledger + Ripple Queue (nối NarrativeDebtLedger)
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
import json, pathlib
from fanfic_pipeline.butterfly.propagator import Ripple

class Divergence(BaseModel):
    id: str
    fact: str
    op: str  # assert|retract
    origin_fic_chapter: int = 1
    cause: str = ""
    tier: int = 1
    scope: str = "personal"
    approved: bool = True

class DivergenceLedger(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    divergences: List[Divergence] = Field(default_factory=list)
    ripples: List[Ripple] = Field(default_factory=list)
    pod: Optional[Any] = None

    # Internal runtime references (not serialized to JSON)
    _propagator: Any = None
    _graph: Any = None
    _policy: Any = None
    _ripple_counter: int = 0

    def bind(self, propagator=None, graph=None, policy=None, pod=None):
        """Inject dependencies for runtime butterfly propagation."""
        self._propagator = propagator
        self._graph = graph
        self._policy = policy
        if pod is not None:
            self.pod = pod
        # Sync ripple counter with existing ripples
        for r in self.ripples:
            if r.id.startswith("RIP:"):
                try:
                    num = int(r.id.split(":")[1])
                    self._ripple_counter = max(self._ripple_counter, num)
                except Exception:
                    pass

    def add_divergence(self, div: Divergence) -> List[Ripple]:
        self.divergences.append(div)
        if not self._propagator or not self._graph or not self._policy:
            return []
        from fanfic_pipeline.butterfly.propagator import ripples_from
        status = self._propagator.propagate(
            self.pod, self.divergences, self._graph, self._policy, current_chapter=div.origin_fic_chapter
        )
        new_ripples = ripples_from(status, self._graph, self._policy, current_chapter=div.origin_fic_chapter)
        # Assign persistent IDs and link to divergence
        for r in new_ripples:
            self._ripple_counter += 1
            r.id = f"RIP:{self._ripple_counter:03d}"
            r.from_divergence = div.id
        self.ripples.extend(new_ripples)
        return new_ripples

    def ripples_due(self, fic_chapter: int) -> List[Ripple]:
        return [r for r in self.ripples if r.status=="open" and r.due_fic_chapter_range and r.due_fic_chapter_range[0] <= fic_chapter <= r.due_fic_chapter_range[1]]

    def overdue(self, fic_chapter: int) -> List[Ripple]:
        return [r for r in self.ripples if r.status=="open" and r.due_fic_chapter_range and r.due_fic_chapter_range[1] < fic_chapter]

    def mark_satisfied(self, ripple_id: str, fic_chapter: int, evidence: str, draft_text: Optional[str] = None):
        for r in self.ripples:
            if r.id == ripple_id:
                if len(evidence) < 5:
                    raise ValueError("evidence must be at least 5 characters")
                if draft_text is not None and evidence not in draft_text:
                    raise ValueError("evidence must be substring of draft")
                r.status = "satisfied"

    def waive(self, ripple_id: str, reason: str, by: str):
        for r in self.ripples:
            if r.id == ripple_id:
                r.status = "waived"

    def save(self, path: str):
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(path).write_text(json.dumps(self.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "DivergenceLedger":
        return cls(**json.loads(pathlib.Path(path).read_text(encoding="utf-8")))

