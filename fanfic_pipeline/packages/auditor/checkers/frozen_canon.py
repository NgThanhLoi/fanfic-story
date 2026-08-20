from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class FrozenCanonChecker(BaseChecker):
    checker_id = "frozen_canon"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if ctx.pod and hasattr(ctx.pod, "invariants"):
            for inv in ctx.pod.invariants:
                if f"không phải {inv}" in draft or f"hủy diệt {inv}" in draft:
                    return CheckResult(
                        checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.0,
                        reason=f"Vi phạm bất biến frozen canon: {inv}",
                        actionable_fix=f"Giữ nguyên sự thật cốt lõi về [{inv}] không được phủ định."
                    )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
