"""
P2.6 — Convergence Policy (SPEC §B6 + B3.1):
- butterfly_gain, inertia_gain, damping, max_depth, threshold, max_open_ripples
- mode soft/hard/none, never_converge list
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json, pathlib

class ConvergenceConfig(BaseModel):
    mode: str = "soft"
    start_canon_chapter: int = 400
    pull_strength: float = 0.3
    never_converge: List[str] = Field(default_factory=list)

class ButterflyPolicy(BaseModel):
    butterfly_gain: float = 1.0
    inertia_gain: float = 1.0
    damping: float = 0.75
    max_depth: int = 5
    threshold: float = 0.12
    max_open_ripples: int = 40
    convergence: ConvergenceConfig = Field(default_factory=ConvergenceConfig)

    @classmethod
    def default(cls) -> "ButterflyPolicy":
        return cls(
            convergence=ConvergenceConfig(mode="soft", start_canon_chapter=400, pull_strength=0.3, never_converge=["FACT:gcv_knows_luc_dao"])
        )

    def is_protected_fact(self, fact_id: str) -> bool:
        return fact_id in self.convergence.never_converge

    def pull_toward_canon(self, fic_chapter: int, canon_time: int) -> float:
        if self.convergence.mode == "none": return 0.0
        if canon_time < self.convergence.start_canon_chapter: return 0.0
        return self.convergence.pull_strength

INERTIA = {"personal": 0.15, "local": 0.35, "faction": 0.60, "world": 0.85}
NECESSITY_TRANSMIT = {"load_bearing": 1.0, "contingent": 0.5, "incidental": 0.0}
