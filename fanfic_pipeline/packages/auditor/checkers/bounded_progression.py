"""
P1 — Bounded Progression checker (P1, spec §2).

Review F-03 + §8: sensory/power payoff phải nằm trong envelope của committed
state; cấm siêu-nhiên-hóa kỹ năng bounded (intent erasure, mental immunity,
radar hóa giác quan...). Driver: ctx.current_state['power_envelope'] (tùy chọn):
{"forbidden_phrases": [...], "max_sensory_range_meters": N}.
"""
import re

from fanfic_pipeline.packages.auditor.base import AuditContext, BaseChecker, CheckResult

# Siêu-nhiên-hóa kỹ năng bounded — bài học wording Tàng Ý (review §8.2)
OVERCLAIM_PATTERNS = [
    (r"(?i)(?:sát\s+ý|ý\s+đồ|tâm\s+niệm)[^.!?]{0,25}(?:xóa|xoá)\s+(?:sạch|đi|hẳn)", "intent erasure"),
    (r"(?i)(?:xóa|xoá)\s+(?:sạch|đi)?\s*(?:sát\s+ý|ý\s+niệm|dấu\s+vết\s+tâm\s+linh)", "intent erasure"),
    (r"(?i)miễn\s+nhiễm\s+(?:với\s+)?(?:tâm\s+thần|ma\s+khí|tâm\s+ma|ý\s+đồ|ảo\s+thuật)", "mental immunity"),
    (r"(?i)(?:đối\s+thủ|kẻ\s+địch)[^.!?]{0,20}không\s+thể\s+cảm\s+nhận\s+(?:được\s+)?(?:bất\s+cứ\s+)?(sát\s+ý|ý\s+đồ)", "conceptual unreadability"),
    (r"(?i)(?:nghe|nhìn)\s+(?:rõ|thấy)\s+(?:từng|mọi)\s+(?:chuyển\s+)?(?:động|vật)\s+(?:trong|ở)\s+(?:phạm\s+vi|bán\s+kính)", "radar senses"),
    (r"(?i)phát\s+hiện\s+(?:trước|sớm)\s+mọi\s+(?:cuộc\s+)?phục\s+kích", "automatic ambush detection"),
]


class BoundedProgressionChecker(BaseChecker):
    checker_id = "bounded_progression"
    severity = "P1"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if not draft or not draft.strip():
            return CheckResult(checker_id=self.checker_id, status="UNKNOWN",
                               severity=self.severity, score=0.5, reason="Draft rỗng")
        state = ctx.current_state if (ctx is not None and isinstance(ctx.current_state, dict)) else {}
        envelope = state.get("power_envelope") or {}
        violations = []
        for pat, label in OVERCLAIM_PATTERNS:
            m = re.search(pat, draft)
            if m:
                violations.append(f"Siêu-nhiên-hóa kỹ năng bounded [{label}]: '{m.group(0)}'")
        for phrase in envelope.get("forbidden_phrases", []) or []:
            if phrase and phrase in draft:
                violations.append(f"Vượt power envelope: '{phrase}'")
        if violations:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity,
                score=0.0, reason="; ".join(violations[:3]),
                actionable_fix="Hạ payoff về mức giai đoạn hiện tại: kỹ năng bounded chỉ "
                               "giảm telegraph/tăng độ khó đọc — không erase/immune/radar. "
                               "Sensory improvement phải bounded và có đào luyện.",
            )
        return CheckResult(checker_id=self.checker_id, status="PASS",
                           severity=self.severity, score=1.0)
