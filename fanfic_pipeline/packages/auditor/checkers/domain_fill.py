"""
P1 — Domain-Fill Guard (P0, spec §2).

Review F-02: canon im lặng về chi tiết (vị trí 9 huyệt Tỵ Khiếu) ⇒ model lấy
hệ thống ngoài đời (huyệt TCM) điền vào = plausible hallucination. Cấm map
hệ riêng-của-canon sang hệ thực tế nếu không có canonicalization receipt trong
ctx.current_state['canonicalized_terms'].
"""
from fanfic_pipeline.packages.auditor.base import AuditContext, BaseChecker, CheckResult
from fanfic_pipeline.packages.governance.topology import normalize_vi, load_default_topology


class DomainFillChecker(BaseChecker):
    checker_id = "domain_fill"
    severity = "P0"
    status = "implemented"

    def __init__(self, topology=None):
        super().__init__()
        self._topology = topology

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        topo = self._topology or load_default_topology()
        if topo is None:
            return CheckResult(checker_id=self.checker_id, status="UNKNOWN",
                               severity=self.severity, score=0.5,
                               reason="aperture_topology.json thiếu — fail-closed")
        if not draft or not draft.strip():
            return CheckResult(checker_id=self.checker_id, status="UNKNOWN",
                               severity=self.severity, score=0.5,
                               reason="Draft rỗng")
        canonicalized = set()
        if isinstance(ctx.current_state, dict):
            canonicalized = set(ctx.current_state.get("canonicalized_terms", []) or [])
        canon_norm = {normalize_vi(c) for c in canonicalized}
        hits = [t for t in topo.find_domain_fill(draft)
                if t not in canon_norm]
        if hits:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity,
                score=0.0,
                reason=f"Điền khoảng trống canon bằng hệ ngoài đời: {hits[:3]}. "
                       f"Canon không chứng minh các huyệt này thuộc hệ khiếu-huyệt của thế giới.",
                actionable_fix="Dùng thuật ngữ trung tính trong-canonical hoặc mô tả cảm giác "
                               "chủ quan; muốn dùng tên TCM phải có canonicalization receipt trước.",
            )
        return CheckResult(checker_id=self.checker_id, status="PASS",
                           severity=self.severity, score=1.0)
