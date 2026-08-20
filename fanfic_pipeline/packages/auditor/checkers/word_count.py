from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class WordCountChecker(BaseChecker):
    checker_id = "word_count"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        words = len(draft.split())
        min_words = 500
        if words < min_words:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity,
                score=words / float(min_words), reason=f"Chương quá ngắn: {words} từ (tối thiểu {min_words} từ)",
                actionable_fix="Mở rộng thêm chi tiết miêu tả bối cảnh và tâm lý nhân vật."
            )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)

