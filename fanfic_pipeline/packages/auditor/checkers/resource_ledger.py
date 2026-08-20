from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class ResourceLedgerChecker(BaseChecker):
    checker_id = "resource_ledger"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        thien_cong = ctx.current_state.get("team_thien_cong", {})
        if isinstance(thien_cong, dict):
            for k, val in thien_cong.items():
                if isinstance(val, (int, float)) and val < 0:
                    return CheckResult(
                        checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.0,
                        reason=f"Thiện công của [{k}] bị âm ({val}).",
                        actionable_fix="Điều chỉnh lại mức tiêu hao thiện công không vượt quá số dư."
                    )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
