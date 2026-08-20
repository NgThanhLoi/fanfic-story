import re
from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class AliveDeadChecker(BaseChecker):
    checker_id = "alive_dead"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        dead_characters = ctx.current_state.get("dead_characters", [])
        for char in dead_characters:
            if re.search(rf"(?<!\w){re.escape(char)}(?!\w)", draft):
                for act in ["nói", "hét", "vung kiếm", "bước ra", "cười"]:
                    if re.search(rf"(?<!\w){re.escape(char)}\s+{re.escape(act)}", draft):
                        return CheckResult(
                            checker_id=self.checker_id, status="FAIL", severity=self.severity, score=0.0,
                            reason=f"Nhân vật đã tử nạn [{char}] nhưng vẫn hành động/đối thoại trong chương.",
                            actionable_fix=f"Xóa hoặc sửa các phân cảnh hành động của {char}."
                        )
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)

