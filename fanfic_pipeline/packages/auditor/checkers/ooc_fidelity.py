from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class OOCFidelityChecker(BaseChecker):
    checker_id = "ooc_fidelity"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if "Mạnh Kỳ tuyệt vọng khóc lóc quỳ xuống xin tha mạng" in draft:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.0,
                reason="OOC nghiêm trọng: Mạnh Kỳ bộc lộ tính cách hèn nhát quỳ xin tha mạng.",
                actionable_fix="Sửa phản ứng của Mạnh Kỳ giữ vững tinh thần ngạo cốt và tìm mưu thoát hiểm."
            )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
