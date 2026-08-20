from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class PODCompatibilityChecker(BaseChecker):
    checker_id = "pod_compatibility"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if ctx.pod and hasattr(ctx.pod, "anchor_chapter"):
            if ctx.chapter_num < ctx.pod.anchor_chapter:
                if "Ma Phật truyền thừa" in draft:
                    return CheckResult(
                        checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.0,
                        reason=f"Xuất hiện rẽ nhánh trước mốc POD (Chương {ctx.pod.anchor_chapter}).",
                        actionable_fix="Đưa các tình tiết rẽ nhánh về đúng sau chương POD."
                    )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
