"""
P1 — Transition Topology checker (P0, spec §2).

Draft-side mirror của premise gate (review F-09): draft không được tuyên bố
mở/skip khiếu ngoài topology canon. Committed state đọc từ ctx.current_state
['opened_apertures']; mọi aperture MỚI tuyên bố trong draft phải là cạnh hợp lệ.
"""
from fanfic_pipeline.packages.auditor.base import AuditContext, BaseChecker, CheckResult
from fanfic_pipeline.packages.governance.topology import load_default_topology


class TransitionTopologyChecker(BaseChecker):
    checker_id = "transition_topology"
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
        committed = []
        if isinstance(ctx.current_state, dict):
            committed = list(ctx.current_state.get("opened_apertures", []) or [])
        violations = topo.validate_artifact(draft, committed)
        if violations:
            first = violations[0]
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity,
                score=0.0,
                reason=f"[{first.kind}] {first.message}",
                actionable_fix="Sửa progression trong draft theo topology canon "
                               f"(thứ tự hợp lệ: {topo.order}); skip cần exception receipt.",
            )
        return CheckResult(checker_id=self.checker_id, status="PASS",
                           severity=self.severity, score=1.0)
