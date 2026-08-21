"""
P1 — Epistemic & World-Fact Boundary Checker (P0, spec §2).

Thay EpistemicLeakChecker. Ba lớp kiểm:
1. Forbidden secrets từ writer_packet (giữ tương thích checker cũ).
2. Spoiler-planner: sự kiện canon ở chương > canon_time_max không được nhắc như
   đã xảy ra (4-lớp-sự-thật của Fate spec).
3. Unconfirmed claims: giả thuyết planner / tên phe-chưa-tiết-lo trong
   ctx.current_state['unconfirmed_claims'] có forbidden_wording — dùng forbidden
   wording = assert thành fact = FAIL.
Nguồn: tools_epistemic_claim_check.py + FATE_FUTURE_CONTROL_SPEC.md.
"""
import re

from fanfic_pipeline.packages.auditor.base import AuditContext, BaseChecker, CheckResult


class EpistemicClaimChecker(BaseChecker):
    checker_id = "epistemic_claim"
    severity = "P0"
    status = "implemented"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if not draft or not draft.strip():
            return CheckResult(checker_id=self.checker_id, status="UNKNOWN",
                               severity=self.severity, score=0.5,
                               reason="Draft rỗng — không thể kiểm epistemic boundary")
        violations = []

        # 1. Secrets từ packet (tương thích EpistemicLeakChecker cũ)
        if ctx.writer_packet is not None and hasattr(ctx.writer_packet, "forbidden"):
            for secret in (ctx.writer_packet.forbidden or []):
                if secret and secret in draft:
                    violations.append(f"Rò rỉ vùng cấm [{secret}]")

        # 2. Spoiler canon-time: draft khẳng định sự kiện canon chưa xảy ra
        canon_time_max = None
        if isinstance(ctx.current_state, dict):
            canon_time_max = ctx.current_state.get("canon_time_max")
        if canon_time_max:
            for m in re.finditer(r"canon\s*ch\.?\s*(\d+)", draft.lower()):
                ch = int(m.group(1))
                if ch > canon_time_max:
                    violations.append(
                        f"Nhắc canon ch.{ch} (> canon_time_max={canon_time_max}) như đã xảy ra — spoiler planner")

        # 3. Unconfirmed claims với forbidden wording
        claims = []
        if isinstance(ctx.current_state, dict):
            claims = ctx.current_state.get("unconfirmed_claims", []) or []
        for claim in claims:
            status = str(claim.get("world_status", "")).upper()
            if status != "UNCONFIRMED":
                continue
            for phrase in claim.get("forbidden_wording", []) or []:
                if phrase and re.search(re.escape(phrase), draft, re.IGNORECASE):
                    violations.append(
                        f"Claim UNCONFIRMED '{claim.get('claim_id', claim.get('claim', '?'))}' "
                        f"bị assert thành fact qua cụm '{phrase}'")

        if violations:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity,
                score=0.0, reason="; ".join(violations[:3]),
                actionable_fix="Tách bạch 4 lớp sự thật: nhân vật biết / suy-diễn được / "
                               "bàn-tay-giấu-sau / spoiler-planner. Chỉ viết những gì "
                               "nhân vật ở mốc này thật sự biết; giả thuyết phải giữ ngữ khí suy đoán.",
            )
        return CheckResult(checker_id=self.checker_id, status="PASS",
                           severity=self.severity, score=1.0)
