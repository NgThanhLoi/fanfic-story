from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class PacingChecker(BaseChecker):
    checker_id = "pacing"
    severity = "P1"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        lines = [l for l in draft.splitlines() if l.strip()]
        if not lines:
            return CheckResult(checker_id=self.checker_id, status="FAIL", severity="P0", score=0.0, reason="Bản thảo trống.")
        dialogue_prefixes = ('"', '“', '”', '‘', '’', "'", '-', '—', '–')
        dialogue_lines = sum(1 for l in lines if l.startswith(dialogue_prefixes))



        ratio = dialogue_lines / len(lines)
        if ratio > 0.85:
            return CheckResult(
                checker_id=self.checker_id, status="WARN", severity=self.severity, score=0.6,
                reason=f"Tỷ lệ đối thoại quá dày ({ratio:.1%}), thiếu miêu tả động tác và môi trường.",
                actionable_fix="Bổ sung thêm miêu tả hành động và biến chuyển tâm lý giữa các câu thoại."
            )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
