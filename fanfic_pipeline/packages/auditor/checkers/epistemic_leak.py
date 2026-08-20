from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class EpistemicLeakChecker(BaseChecker):
    checker_id = "epistemic_leak"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        forbidden = []
        if ctx.writer_packet and hasattr(ctx.writer_packet, "forbidden"):
            forbidden = ctx.writer_packet.forbidden or []
        for secret in forbidden:
            if secret in draft:
                return CheckResult(
                    checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.0,
                    reason=f"Rò rỉ tri thức vùng cấm (Epistemic Leak): [{secret}]",
                    actionable_fix=f"Xóa bỏ mọi chi tiết để lộ bí mật [{secret}] khỏi góc nhìn nhân vật."
                )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
