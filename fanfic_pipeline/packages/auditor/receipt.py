"""
Audit Receipt and reporting models.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from fanfic_pipeline.packages.auditor.base import CheckResult

class DimensionResult(BaseModel):
    name: str
    passed: bool
    score: float = 1.0
    reason: str = ""
    issues: List[str] = Field(default_factory=list)

class AuditReceipt(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")
    chapter_number: int
    draft_hash: str
    verdict: str = "PASS"  # PASS | REVISE | REJECT
    overall_passed: bool = True
    score: float = 100.0
    check_results: List[CheckResult] = Field(default_factory=list)
    results: List[DimensionResult] = Field(default_factory=list)
    revision_directives: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"
