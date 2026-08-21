"""
P1 — Relationship Dynamics checker (P1, spec §2).

Nhịp quan hệ trong draft phải khớp intimacy_level/current_dynamic committed
(ctx.current_state['relationships']). Tiến nhanh hơn mà không có sự kiện chứng
cứ trong chương (ctx.current_state['relationship_events']) = FAIL.
"""
import re

from fanfic_pipeline.packages.auditor.base import AuditContext, BaseChecker, CheckResult

# Dấu hiệu tiến nhanh quan hệ trong văn: tuyên bố tin tưởng/tình cảm tuyệt đối
RUSH_PATTERNS = [
    (r"(?i)(?:tin\s+tưởng|tin\s+yêu)\s+(?:tuyệt\s+đối|không\s+gì\s+so\s+được)", "tin tưởng tuyệt đối"),
    (r"(?i)(?:yêu|thương)\s+(?:nhất|sâu\s+sắc)\s+đời", "tuyên bố tình cảm sâu sắc"),
    (r"(?i)sinh\s+tử\s+đồng\s+cách", "cam kết sinh tử"),
]


class RelationshipDynamicsChecker(BaseChecker):
    checker_id = "relationship_dynamics"
    severity = "P1"
    status = "implemented"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if not draft or not draft.strip():
            return CheckResult(checker_id=self.checker_id, status="UNKNOWN",
                               severity=self.severity, score=0.5, reason="Draft rỗng")
        state = ctx.current_state if isinstance(ctx.current_state, dict) else {}
        relationships = state.get("relationships") or []
        events = state.get("relationship_events") or []
        violations = []
        for rel in relationships:
            pair = rel.get("pair") or []
            if len(pair) < 2:
                continue
            level = int(rel.get("intimacy_level", 0))
            # Cặp intimacy thấp mà văn tuyên bố đỉnh cao quan hệ → rush
            if level <= 3:
                for pat, label in RUSH_PATTERNS:
                    for name in pair:
                        # tên một bên + pattern trong cùng câu
                        for m in re.finditer(rf"[^\n.!?]*{re.escape(name)}[^\n.!?]*", draft):
                            sentence = m.group(0)
                            if re.search(pat, sentence):
                                has_event = any(e.get("pair") == pair for e in events)
                                if not has_event:
                                    violations.append(
                                        f"{pair[0]}×{pair[1]} (intimacy={level}): "
                                        f"'{label}' không có sự kiện chứng cứ trong chương")
                                break
        if violations:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity,
                score=0.0, reason="; ".join(violations[:3]),
                actionable_fix="Quan hệ tiến từng bậc kèm sự kiện chứng cứ; muốn nhảy bậc "
                               "phải ghi relationship_events receipt trước khi viết.",
            )
        return CheckResult(checker_id=self.checker_id, status="PASS",
                           severity=self.severity, score=1.0)
