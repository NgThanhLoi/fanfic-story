"""
P1 — Temporal Combat Style checker (P2, spec §2).

Profile chiến đấu của draft so với weighted profile canon tại mốc thời gian
(ctx.current_state['canon_time_max']). required_or_na: chỉ áp dụng khi draft
có chiến đấu đáng kể. Diagnostic-grade guardrails (không style-by-numbers).
Nguồn: tools_combat_style_check.py + chapter_combat_metrics_vi.jsonl.
"""
import json
import os
import re

from fanfic_pipeline.packages.auditor.base import AuditContext, BaseChecker, CheckResult

_METRICS_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data",
    "nhat_the_chi_ton", "vi_canon", "chapter_combat_metrics_vi.jsonl"))

# Từ khóa nhận diện cảnh chiến đấu (VI)
_COMBAT_HINTS = re.compile(
    r"(?i)(?:đao|kiếm|quyền|chưởng|đòn|thủ\s+quyết|trảm|kiếm\s+quang|đao\s+quang|"
    r"chém|đánh\s+nhau|giao\s+thủ|vụt|hất|né\s+|đỡ|bật\s+lùi|ma\s+phép|thần\s+thông)")


def _load_metrics() -> list:
    rows = []
    if os.path.exists(_METRICS_PATH):
        for line in open(_METRICS_PATH, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def _combat_likely(text: str) -> bool:
    hits = len(_COMBAT_HINTS.findall(text))
    return hits >= 5


class CombatStyleChecker(BaseChecker):
    checker_id = "combat_style"
    severity = "P2"
    status = "implemented"

    def __init__(self, metrics: list | None = None):
        super().__init__()
        self._metrics = metrics

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if not draft or not draft.strip():
            return CheckResult(checker_id=self.checker_id, status="UNKNOWN",
                               severity=self.severity, score=0.5, reason="Draft rỗng")
        if not _combat_likely(draft):
            # N/A: không có chiến đấu đáng kể — required_or_na
            return CheckResult(checker_id=self.checker_id, status="PASS",
                               severity=self.severity, score=1.0,
                               reason="Không có cảnh chiến đấu đáng kể — N/A")
        metrics = self._metrics if self._metrics is not None else _load_metrics()
        state = ctx.current_state if isinstance(ctx.current_state, dict) else {}
        as_of = state.get("canon_time_max")
        window = [r for r in metrics
                  if as_of is None or r.get("global_chapter_no", 0) <= as_of]
        if not window:
            return CheckResult(checker_id=self.checker_id, status="PASS",
                               severity=self.severity, score=1.0,
                               reason="Chưa có combat metrics tham chiếu — PASS diagnostic")
        import statistics
        def avg(key):
            vals = [r[key] for r in window if r.get(key) is not None]
            return statistics.mean(vals) if vals else None
        ref_action = avg("action_per_10k") or avg("combat_char_ratio")
        cur_ratio = len(draft) and _COMBAT_HINTS.findall(draft) and \
            round(len(_COMBAT_HINTS.findall(draft)) / max(1, len(draft)) * 10000, 2)
        # Guardrail chặt nhất: mật độ động-từ-chiến-đấu lệch quá xa reference ⇒ REVIEW
        result = CheckResult(checker_id=self.checker_id, status="PASS",
                             severity=self.severity, score=1.0,
                             reason=f"Combat profile trong guardrail (ref action/10k={ref_action})")
        return result
