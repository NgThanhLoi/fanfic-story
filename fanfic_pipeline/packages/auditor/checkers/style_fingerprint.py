"""
P1 — Style Fingerprint checker (P0, spec §2 + §4.4).

Hai mode qua ctx.current_state['style_mode'] (mặc định fanfic_voice):
- fanfic_voice: guard band percentile — FAIL luôn chặn, REVIEW chặn trừ khi có
  style_manual_review receipt trong current_state.
- canon_mimicry: thêm style fidelity ≥ canon_min_fidelity (mặc định 90);
  REVIEW cũng chặn như FAIL (không có lối thoát manual-review).
Nguồn: tools_style_check.py; fingerprint là dẫn xuất từ corpus VI (P2 refingerprint).
"""
import re
import statistics

from fanfic_pipeline.packages.auditor.base import AuditContext, BaseChecker, CheckResult

_WORD_RE = re.compile(r"[A-Za-zÀ-ỹĐđ]+")
_SENT_RE = re.compile(r"[^.!?…。！？\n]+(?:[.!?…]+|$)")

FORBIDDEN_ENGLISH = [
    "baseline", "tradecraft", "profiling", "workflow", "persona",
    "professional_suspicion", "counter-surveillance",
]

# Guard band (TARGET) và hard band (REVIEW) — chuẩn tools_style_check.py
TARGET_BANDS = {
    "avg_sentence_words": (18, 38),
    "avg_paragraph_chars": (100, 240),
    "comma_per_10k_chars": (130, 250),
    "short_sentence_ratio_lt10": (0.0, 0.35),
    "very_short_paragraph_ratio_lt60": (0.0, 0.18),
}
HARD_BANDS = {
    "avg_sentence_words": (14, 45),
    "avg_paragraph_chars": (80, 300),
    "comma_per_10k_chars": (100, 320),
    "short_sentence_ratio_lt10": (0.0, 0.50),
    "very_short_paragraph_ratio_lt60": (0.0, 0.35),
}


def analyze_text(text: str) -> dict:
    body = "\n".join(
        x for x in text.splitlines()
        if not x.startswith("#") and not x.startswith(">")
        and x.strip() not in ("***", "---", "___")
    ).strip()
    paragraphs = [p.strip() for p in body.splitlines() if p.strip()]
    sentences = [m.group(0).strip() for m in _SENT_RE.finditer(body) if m.group(0).strip()]
    sent_words = [len(_WORD_RE.findall(s)) for s in sentences]
    low = body.lower()
    forbidden = {w: len(re.findall(rf"(?<![A-Za-z]){re.escape(w)}(?![A-Za-z])", low))
                 for w in FORBIDDEN_ENGLISH}
    forbidden = {k: v for k, v in forbidden.items() if v}
    return {
        "paragraph_count": len(paragraphs),
        "sentence_count": len(sentences),
        "avg_sentence_words": round(statistics.mean(sent_words), 2) if sent_words else 0,
        "avg_paragraph_chars": round(statistics.mean(map(len, paragraphs)), 2) if paragraphs else 0,
        "comma_per_10k_chars": round(body.count(",") / max(1, len(body)) * 10000, 2),
        "short_sentence_ratio_lt10": round(sum(x < 10 for x in sent_words) / max(1, len(sent_words)), 4),
        "very_short_paragraph_ratio_lt60": round(sum(len(p) < 60 for p in paragraphs) / max(1, len(paragraphs)), 4),
        "em_dash_count": body.count("—"),
        "forbidden_english_jargon": forbidden,
    }


def style_fidelity(metrics: dict, reference: dict) -> float:
    """Weighted-distance fidelity 0-100 giữa draft metrics và fingerprint gốc.
    Mỗi metric quy về percentile-offset tương đối so với giá trị gốc; tổng hợp
    theo trọng số bằng nhau (công thức khai báo, tái-lập-được)."""
    keys = ["avg_sentence_words", "avg_paragraph_chars", "comma_per_10k_chars"]
    scores = []
    for k in keys:
        cur, ref = metrics.get(k), reference.get(k)
        if not cur or not ref:
            continue
        offset = abs(cur - ref) / ref          # lệch tương đối
        # đường cong dịu: lệch ≤25% vẫn tính ≥90 điểm (biến thiên tự nhiên của văn),
        # suy tuyến tính về 0 ở lệch 100%.
        scores.append(max(0.0, 1.0 - max(0.0, offset - 0.25) / 0.75))
    # ratio metrics: lệch tuyệt đối, cùng độ dịu (0.08 ≈ bậc tự nhiên)
    for k in ("short_sentence_ratio_lt10", "very_short_paragraph_ratio_lt60"):
        cur, ref = metrics.get(k), reference.get(k)
        if cur is None or ref is None:
            continue
        delta = abs(cur - ref)
        scores.append(max(0.0, 1.0 - max(0.0, delta - 0.08) / 0.32))
    if not scores:
        return 50.0
    return round(sum(scores) / len(scores) * 100, 1)


class StyleFingerprintChecker(BaseChecker):
    checker_id = "style_fingerprint"
    severity = "P0"
    status = "implemented"

    def __init__(self, reference: dict | None = None):
        super().__init__()
        self._reference = reference or {
            "avg_sentence_words": 27.45,
            "avg_paragraph_chars": 165.61,
            "comma_per_10k_chars": 196.61,
            "short_sentence_ratio_lt10": 0.1994,
            "very_short_paragraph_ratio_lt60": 0.0808,
        }

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        if not draft or not draft.strip():
            return CheckResult(checker_id=self.checker_id, status="UNKNOWN",
                               severity=self.severity, score=0.5, reason="Draft rỗng")
        state = ctx.current_state if isinstance(ctx.current_state, dict) else {}
        mode = state.get("style_mode", "fanfic_voice")
        metrics = analyze_text(draft)

        fails, reviews = [], []
        for name, value in metrics.items():
            if name not in TARGET_BANDS:
                continue
            tlo, thi = TARGET_BANDS[name]
            hlo, hhi = HARD_BANDS[name]
            if not (tlo <= value <= thi):
                if hlo <= value <= hhi:
                    reviews.append(f"{name}={value} ngoài target band [{tlo},{thi}] (hard band)")
                else:
                    fails.append(f"{name}={value} vượt cả hard band [{hlo},{hhi}]")
        if metrics["forbidden_english_jargon"]:
            fails.append(f"Tiếng Anh lạ trong văn: {list(metrics['forbidden_english_jargon'])[:4]}")
        if metrics["em_dash_count"] > 6:
            reviews.append(f"em-dash x{metrics['em_dash_count']} (>6)")

        fidelity = style_fidelity(metrics, self._reference)
        min_fid = float(state.get("canon_min_fidelity", 90))
        manual_ok = bool(state.get("style_manual_review"))

        if mode == "canon_mimicry":
            # REVIEW cũng chặn như FAIL; không có lối thoát manual review
            if fails or reviews:
                detail = "; ".join((fails + reviews)[:3])
                return CheckResult(
                    checker_id=self.checker_id, status="FAIL", severity=self.severity,
                    score=0.0,
                    reason=f"[canon_mimicry] {detail}. Style fidelity={fidelity} "
                           f"(yêu cầu ≥{min_fid}).",
                    actionable_fix="Viết lại bám excerpt mẫu cùng arc/cảnh-loại; chỉnh metric "
                                   "lệch hướng nào sửa hướng đó.",
                )
            if fidelity < min_fid:
                return CheckResult(
                    checker_id=self.checker_id, status="FAIL", severity=self.severity,
                    score=max(0.0, fidelity / 100),
                    reason=f"[canon_mimicry] Style fidelity={fidelity} < {min_fid}",
                    actionable_fix="Tăng độ bám mẫu: nhịp câu/đoạn, mật độ dấu phẩy, tỉ lệ thoại.",
                )
            return CheckResult(checker_id=self.checker_id, status="PASS",
                               severity=self.severity, score=1.0,
                               reason=f"fidelity={fidelity}")

        # fanfic_voice
        if fails:
            return CheckResult(
                checker_id=self.checker_id, status="FAIL", severity=self.severity,
                score=0.0, reason="; ".join(fails[:3]),
                actionable_fix="Đưa các metric về trong hard band; FAIL luôn chặn.",
            )
        if reviews and not manual_ok:
            return CheckResult(
                checker_id=self.checker_id, status="REVISE", severity=self.severity,
                score=0.5, reason="; ".join(reviews[:3]),
                actionable_fix="Sửa về target band hoặc nộp style_manual_review receipt "
                               "(ACCEPT_STYLE_REVIEW + lý do).",
            )
        return CheckResult(checker_id=self.checker_id, status="PASS",
                           severity=self.severity, score=1.0)
