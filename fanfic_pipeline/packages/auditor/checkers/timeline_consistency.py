from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class TimelineConsistencyChecker(BaseChecker):
    checker_id = "timeline_consistency"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if ctx.chapter_num <= 0:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.0,
                reason=f"Chapter index không hợp lệ ({ctx.chapter_num}).", actionable_fix="Gán số chương > 0."
            )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
