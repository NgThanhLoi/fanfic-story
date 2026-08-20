from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class HashBranchChecker(BaseChecker):
    checker_id = "hash_branch"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if ctx.writer_packet and hasattr(ctx.writer_packet, "packet_hash"):
            if not ctx.writer_packet.packet_hash:
                return CheckResult(
                    checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.0,
                    reason="SealedWriterPacket thiếu packet_hash hợp lệ.",
                    actionable_fix="Tạo lại writer packet có chữ ký SHA-256."
                )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
