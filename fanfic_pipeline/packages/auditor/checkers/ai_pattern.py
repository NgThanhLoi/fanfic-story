from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class AIPatternChecker(BaseChecker):
    checker_id = "ai_pattern"
    severity = "P1"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        lines = [l.strip() for l in draft.splitlines() if len(l.strip()) >= 10]
        for i in range(len(lines) - 2):
            if lines[i] == lines[i+1] == lines[i+2]:
                return CheckResult(
                    checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.3,
                    reason=f"Phát hiện vòng lặp suy thoái lặp lại nguyên văn: {lines[i][:40]}...",
                    actionable_fix="Xóa bỏ đoạn văn bị lặp lại nhiều lần liên tiếp."
                )
        tail = draft[-250:].lower()
        if "tương lai sẽ ra sao, hãy chờ xem" in tail or "cuộc hành trình chỉ mới bắt đầu" in tail:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.6,
                reason="Đoạn kết chương bị dính câu kết sáo rỗng AI (tail collapse).",
                actionable_fix="Sửa câu kết chương thành hành động cụ thể hoặc hook tình tiết."
            )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
