"""
Base interfaces and models for the Modular Audit System.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict

class CheckResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")
    checker_id: str
    status: str = "PASS"  # PASS | FAIL | WARN | UNKNOWN
    severity: str = "P1"  # P0 (blocker) | P1 (high) | P2 (medium) | P3 (low)
    score: float = 1.0    # 0.0 .. 1.0
    reason: str = ""
    actionable_fix: str = ""  # Specific directive for Writer Agent rewrite

class AuditContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")
    chapter_num: int = 1
    draft_text: str = ""
    current_state: Dict[str, Any] = Field(default_factory=dict)
    prior_state: Optional[Dict[str, Any]] = None
    writer_packet: Optional[Any] = None
    pod: Optional[Any] = None
    ledger: Optional[Any] = None
    canon_store: Optional[Any] = None
    enrichment_store: Optional[Any] = None
    author_instruction: str = ""

class BaseChecker(ABC):
    checker_id: str = "base_checker"
    severity: str = "P1"
    status: str = "implemented"  # implemented | stub | disabled

    @abstractmethod
    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        pass
