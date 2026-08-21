"""
P1 — Meta-Leak Guard (P0, spec §2).

Văn chương KHÔNG được chứa nhãn ngoài-vùng-truyện: "canon", nhãn pipeline
(planner/writer/receipt/snapshot/commit...), trạng thái power (READY/PASS/FAIL),
"quỹ đạo vốn có"... Canon preservation thuộc về receipts & planning artifacts,
không bao giờ thuộc về lời kể. Strong hit = FAIL.
Nguồn: tools_meta_leak_check.py + review §PRODUCTION pipeline "Hard failures".
"""
import re

from fanfic_pipeline.packages.auditor.base import AuditContext, BaseChecker, CheckResult

STRONG_PATTERNS = [
    (r"(?i)\bcanon\b", "out_of_world_canon_label"),
    (r"(?i)\beconomy\b", "planner_economy_label"),
    (r"(?i)\b(?:BASIC|FOUNDATION|UNMASTERED|READY|PASS|FAIL|REVIEW|BLOCK)\b",
     "pipeline_or_power_state_label"),
    (r"(?i)\b(?:planner|writer|provenance|receipt|snapshot|commit|routing|route|scope|tier|build)\b",
     "pipeline_lexeme"),
    (r"(?i)quỹ đạo\s+(?:vốn\s+có|ban\s+đầu|cũ|canon)", "canon_trajectory_phrase"),
    (r"(?i)(?:trở|quay)\s+(?:về|lại)\s+quỹ\s+đạo", "canon_trajectory_phrase"),
    (r"(?i)(?:đúng|theo)\s+(?:tuyến|mốc)\s+canon", "canon_route_phrase"),
    (r"(?i)(?:theo|giống)\s+(?:nguyên\s+tác|kịch\s+bản)", "source_script_awareness"),
    (r"(?i)kết\s+quả\s+canon", "out_of_world_canon_result"),
    (r"(?i)lựa\s+chọn\s+canon", "out_of_world_canon_choice"),
    (r"(?i)đoạn\s+tiếp\s+theo\b", "chapter_structure_meta"),
]

WEAK_PATTERNS = [
    (r"(?i)nhân\s+vật\s+chính", "possible_story_role_meta"),
    (r"(?i)cốt\s+truyện", "possible_story_meta"),
    (r"(?i)lịch\s+sử\s+vốn\s+có", "possible_fixed_history_meta"),
    (r"(?i)như\s+vốn\s+phải\s+xảy\s+ra", "possible_script_awareness"),
]


class MetaLeakChecker(BaseChecker):
    checker_id = "meta_leak"
    severity = "P0"
    status = "implemented"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if not draft or not draft.strip():
            return self._unknown("Draft rỗng — không thể kiểm meta-leak")
        strong_hits = []
        weak_hits = []
        for pat, label in STRONG_PATTERNS:
            m = re.search(pat, draft)
            if m:
                strong_hits.append((label, m.group(0)))
        for pat, label in WEAK_PATTERNS:
            m = re.search(pat, draft)
            if m:
                weak_hits.append((label, m.group(0)))
        if strong_hits:
            label, hit = strong_hits[0]
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity,
                score=0.0,
                reason=f"Meta-leak: văn chứa nhãn ngoài-vùng-truyện [{label}]: '{hit}'. "
                       f"Canon preservation chỉ nằm ở receipts/planning, không nằm trong lời kể.",
                actionable_fix=f"Xóa/diễn đạt lại mọi cụm ngoài-vùng-truyện ({len(strong_hits)} strong hit). "
                               f"Nhân vật và người kể không được biết mình đang trong một truyện.",
            )
        if weak_hits:
            label, hit = weak_hits[0]
            return CheckResult(
                checker_id=self.checker_id, status="WARN", severity=self.severity,
                score=0.7,
                reason=f"Nghi vấn meta ({label}): '{hit}' — cần rà tay.",
                actionable_fix="Đổi cách diễn đạt nếu không phục vụ chủ đích nghệ thuật.",
            )
        return CheckResult(checker_id=self.checker_id, status="PASS",
                           severity=self.severity, score=1.0)

    def _unknown(self, reason: str) -> CheckResult:
        return CheckResult(checker_id=self.checker_id, status="UNKNOWN",
                           severity=self.severity, score=0.5, reason=reason)
