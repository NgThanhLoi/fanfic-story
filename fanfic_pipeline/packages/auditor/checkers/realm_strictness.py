from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext
from fanfic_pipeline.packages.canon.power_ladder import can_fly

class RealmStrictnessChecker(BaseChecker):
    checker_id = "realm_strictness"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        realms = ctx.current_state.get("character_realms", {})
        for char, realm in realms.items():
            if char in draft and not can_fly(realm):
                for fly_term in ["ngự không phi hành", "bay lên trời", "đạp không mà đi", "lăng không phi hành"]:
                    if f"{char} {fly_term}" in draft:
                        return CheckResult(
                            checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.0,
                            reason=f"Nhân vật [{char}] ở cảnh giới [{realm}] chưa thể ngự không phi hành.",
                            actionable_fix=f"Sửa hành động ngự không của {char} thành khinh công bộ pháp trên mặt đất."
                        )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
