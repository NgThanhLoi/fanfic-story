"""
P1 — Identity Reveal checker (P0, spec §2).

Bí danh spoiler-sensitive (identity_registry.jsonl) xuất hiện trong draft khi
canon_time chưa tới reveal_chapter = FAIL. Intra-chapter fail-closed.
Nguồn: identity_registry.jsonl + review P4.2.4.
"""
import json
import os

from fanfic_pipeline.packages.auditor.base import AuditContext, BaseChecker, CheckResult
from fanfic_pipeline.packages.governance.topology import normalize_vi


def _load_registry() -> list:
    p = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data",
                     "nhat_the_chi_ton", "identity_registry.jsonl")
    p = os.path.normpath(p)
    rows = []
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


class IdentityRevealChecker(BaseChecker):
    checker_id = "identity_reveal"
    severity = "P0"
    status = "implemented"

    def __init__(self, registry: list | None = None):
        super().__init__()
        self._registry = registry

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        registry = self._registry if self._registry is not None else _load_registry()
        if not draft or not draft.strip():
            return CheckResult(checker_id=self.checker_id, status="UNKNOWN",
                               severity=self.severity, score=0.5, reason="Draft rỗng")
        state = ctx.current_state if isinstance(ctx.current_state, dict) else {}
        canon_time = state.get("canon_time_max")
        norm_draft = normalize_vi(draft)
        violations = []
        for row in registry:
            if not row.get("spoiler_sensitive") and canon_time is None:
                continue  # không spoiler-sensitive và không có mốc thời gian → bỏ qua nhanh
            reveal_ch = row.get("reveal_chapter")
            if canon_time is not None and reveal_ch is not None and canon_time < reveal_ch:
                for surface in list(row.get("surfaces_vi", [])) + list(row.get("surfaces_zh", [])):
                    if surface and normalize_vi(surface) in norm_draft:
                        violations.append(
                            f"'{surface}' ({row.get('relation_type')}) tiết lộ trước "
                            f"reveal_chapter={reveal_ch} (canon_time={canon_time})")
        if violations:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity,
                score=0.0, reason="; ".join(violations[:3]),
                actionable_fix="Thay bí danh bằng cách xưng hô hợp mốc thời gian; "
                               "bí danh chỉ xuất hiện sau cảnh tiết lộ tương ứng.",
            )
        return CheckResult(checker_id=self.checker_id, status="PASS",
                           severity=self.severity, score=1.0)
