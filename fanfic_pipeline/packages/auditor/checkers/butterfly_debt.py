from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class ButterflyDebtChecker(BaseChecker):
    checker_id = "butterfly_debt"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if ctx.ledger and hasattr(ctx.ledger, "ripples"):
            # Ripple schema: status open|due|satisfied|overdue|waived + due_fic_chapter_range [start, end]
            if hasattr(ctx.ledger, "overdue"):
                overdue = ctx.ledger.overdue(ctx.chapter_num)
            else:
                overdue = [r for r in ctx.ledger.ripples
                           if getattr(r, "status", "open") in ("open", "due", "overdue")
                           and getattr(r, "due_fic_chapter_range", None)
                           and r.due_fic_chapter_range[1] < ctx.chapter_num]
            if len(overdue) > 5:
                return CheckResult(
                    checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.5,
                    reason=f"Tích tụ quá nhiều ({len(overdue)}) Ripple quá hạn chưa xử lý.",
                    actionable_fix="Hiện thực hóa hoặc làm rõ tác động của các ripple quá hạn."
                )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
