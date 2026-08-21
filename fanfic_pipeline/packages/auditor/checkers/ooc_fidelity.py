"""
P1 — OOC Fidelity checker viết lại (P0, spec §2).

Driver dữ liệu từ voice profile (data/nhat_the_chi_ton/character_voice_profiles.yaml
hoặc ctx.current_state['voice_rules']): ma trận xưng-hô/hào-khí theo nhân vật,
hành-động-bị-cấm theo trạng thái. Violation phải chỉ ra được evidence span.
LLM-critic chỉ còn là lớp advisory phía trên (INV-7).
"""
import re

from fanfic_pipeline.packages.auditor.base import AuditContext, BaseChecker, CheckResult
from fanfic_pipeline.packages.governance.topology import normalize_vi

# Fallback rules khi project chưa khai voice_rules — rút từ CHARACTER_VOICES cốt lõi
DEFAULT_FORBIDDEN_ACTIONS = {
    "Mạnh Kỳ": [
        # ngạo cốt + mưu lược: không quỳ xin tha, không hèn nhát tuyệt đối
        {"pattern": r"(?i)(?:quỳ|gối\s+đầu)\s+(?:xuống\s+)?(?:xin|cầu)\s+(?:tha|sống)",
         "reason": "Mạnh Kỳ bộc lộ hèn nhát quỳ cầu — trái ngạo cốt nhân vật"},
        {"pattern": r"(?i)Mạnh\s+Kỳ.{0,30}(?:khóc\s+lóc|nước\s+mắt\s+dàn\s+trà).{0,20}xin\s+tha",
         "reason": "Khóc lóc xin tha — OOC nghiêm trọng"},
    ],
    "Giang Chỉ Vi": [
        {"pattern": r"(?i)Giang\s+Chỉ\s+Vi.{0,25}(?:sợ\s+hãi|run\s+rẩy)\s+(?:vô\s+cùng|hết\s+ức)",
         "reason": "Giang Chỉ Vi mất khí chất kiếm khách tự tin"},
    ],
}


class OOCFidelityChecker(BaseChecker):
    checker_id = "ooc_fidelity"
    severity = "P0"
    status = "implemented"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if not draft or not draft.strip():
            return CheckResult(checker_id=self.checker_id, status="UNKNOWN",
                               severity=self.severity, score=0.5, reason="Draft rỗng")
        state = ctx.current_state if isinstance(ctx.current_state, dict) else {}
        rules = state.get("voice_rules") or DEFAULT_FORBIDDEN_ACTIONS
        violations = []
        for character, checks in rules.items():
            for rule in checks or []:
                pat = rule.get("pattern") if isinstance(rule, dict) else rule
                reason = rule.get("reason", "vi phạm tính cách cơ bản") if isinstance(rule, dict) else ""
                m = re.search(pat, draft)
                if m:
                    violations.append(f"{character}: {reason} — evidence '{m.group(0)[:60]}'")
        if violations:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity,
                score=0.0, reason="; ".join(violations[:3]),
                actionable_fix="Sửa phản ứng về đúng hào-khí/xưng-hô cốt lõi của nhân vật; "
                               "mọi drift tính cách cần causal receipt trong arc_ledger.",
            )
        return CheckResult(checker_id=self.checker_id, status="PASS",
                           severity=self.severity, score=1.0)
