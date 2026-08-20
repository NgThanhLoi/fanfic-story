"""
P2.1 — POD (SPEC §B2.1): Point of Divergence dữ liệu hoá
- anchor_canon_chapter, kind, scope, intensity, changed_facts, protected_invariants, author_intent, convergence_target
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import json, pathlib

class ChangedFact(BaseModel):
    op: str  # assert | retract
    fact: str
    at_fic_chapter: int = 1

class ConvergenceTarget(BaseModel):
    canon_chapter: int = 400
    mode: str = "soft"  # none | soft | hard

class POD(BaseModel):
    id: str = "POD:001"
    anchor_canon_chapter: int = 18
    statement: str = ""
    kind: str = "epistemic"  # epistemic|action|survival|acquisition|relationship|timing|presence
    scope: str = "personal"  # personal|local|faction|world
    intensity: float = 0.7
    changed_facts: List[ChangedFact] = Field(default_factory=list)
    protected_invariants: List[str] = Field(default_factory=list)
    author_intent: str = ""
    convergence_target: ConvergenceTarget = Field(default_factory=ConvergenceTarget)

    def save(self, path: str):
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(path).write_text(json.dumps(self.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "POD":
        return cls(**json.loads(pathlib.Path(path).read_text(encoding="utf-8")))

# Worked example POD:001 from SPEC §B8
POD_001 = POD(
    id="POD:001",
    anchor_canon_chapter=18,
    statement="Tại canon ch.18, Mạnh Kỳ tiết lộ thân phận Lục Đạo Luân Hồi cho Giang Chỉ Vi",
    kind="epistemic",
    scope="personal",
    intensity=0.7,
    changed_facts=[
        ChangedFact(op="assert", fact="FACT:gcv_knows_luc_dao", at_fic_chapter=1),
        ChangedFact(op="retract", fact="FACT:gcv_ignorant_luc_dao", at_fic_chapter=1),
    ],
    protected_invariants=["INV:001", "INV:010"],
    author_intent="Đổi quan hệ Mạnh Kỳ - Giang Chỉ Vi, KHÔNG đổi cục diện Cửu Châu",
    convergence_target=ConvergenceTarget(canon_chapter=400, mode="soft"),
)
