"""
Audit Runner: Executes modular checkers, calculates score, generates actionable revision directives, and enforces fail-closed verdict.
"""
import hashlib
from typing import Dict, Any, List, Optional
from fanfic_pipeline.packages.auditor.base import AuditContext, CheckResult
from fanfic_pipeline.packages.auditor.registry import CheckerRegistry
from fanfic_pipeline.packages.auditor.receipt import AuditReceipt, DimensionResult

class AuditRunner:
    def __init__(self, registry: Optional[CheckerRegistry] = None):
        self.registry = registry or CheckerRegistry()

    def evaluate(self, draft_text: str, ctx: Optional[AuditContext] = None) -> AuditReceipt:
        if ctx is None:
            ctx = AuditContext(draft_text=draft_text)
        else:
            ctx.draft_text = draft_text

        check_results: List[CheckResult] = []
        revision_directives: List[str] = []
        has_p0_fail = False
        total_score_sum = 0.0

        checkers = self.registry.list_checkers()
        for checker in checkers:
            res = checker.check(draft_text, ctx)
            check_results.append(res)
            total_score_sum += res.score

            if res.status in ("FAIL", "UNKNOWN") and res.severity == "P0":
                has_p0_fail = True

            if res.actionable_fix:
                revision_directives.append(f"[{res.checker_id.upper()}]: {res.actionable_fix}")

        avg_score = (total_score_sum / len(checkers) * 100.0) if checkers else 100.0
        
        # Fail-closed decision
        if has_p0_fail:
            verdict = "REVISE"
            passed = False
        elif avg_score < 75.0:
            verdict = "REVISE"
            passed = False
        else:
            verdict = "PASS"
            passed = True

        draft_hash = hashlib.sha256(draft_text.encode("utf-8")).hexdigest()[:16]

        # Compatibility results for old tests
        compat_results = [
            DimensionResult(
                name=r.checker_id,
                passed=(r.status == "PASS"),
                score=r.score,
                reason=r.reason,
                issues=[r.reason] if r.reason else []
            )
            for r in check_results
        ]

        return AuditReceipt(
            chapter_number=ctx.chapter_num,
            draft_hash=draft_hash,
            verdict=verdict,
            overall_passed=passed,
            score=round(avg_score, 1),
            check_results=check_results,
            results=compat_results,
            revision_directives=revision_directives
        )
