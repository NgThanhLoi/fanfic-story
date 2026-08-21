"""
P4.5 — Style Rewrite Loop (spec §4.4 mở rộng).

Vòng lặp có mục tiêu: draft → đo style metrics → sinh directive CỤ THỂ cho
metric nào lệch/hướng nào → LLM rewrite → re-measure. Dừng khi:
- fidelity ≥ target VÀ không còn hard-band FAIL, hoặc
- hết max_rounds, hoặc
- không cải thiện (fidelity mới ≤ cũ) — giữ bản tốt nhất.

Fail-closed: sau loop vẫn FAIL ⇒ trả kèm receipt để audit gate chặn như thường.
"""
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from fanfic_pipeline.packages.retrieval.style_profile import analyze_text, fidelity


# ---- directive generation ----

def style_directives(metrics: Dict[str, Any], reference: Dict[str, Any]) -> List[str]:
    """Sinh chỉ dẫn sửa CỤ THỂ theo metric lệch — feed thẳng vào LLM rewrite."""
    directives: List[str] = []
    sw, ref_sw = metrics.get("avg_sentence_words") or 0, reference.get("avg_sentence_words") or 27
    if sw < ref_sw * 0.85:
        directives.append(
            f"Câu đang quá ngắn ({sw} từ/câu, chuẩn canon ~{ref_sw}). GỘP các câu ngắn "
            f"liền nhau thành câu dài 25–35 từ, nối mệnh đề bằng dấu phẩy/từ nối "
            f"(và, mà, rồi, khiến, khiến cho, tựa như).")
    elif sw > ref_sw * 1.3:
        directives.append(
            f"Câu đang quá dài ({sw} từ/câu, chuẩn canon ~{ref_sw}). CHẺ các câu quá dài "
            f"thành câu 20–32 từ; giữ nhịp thoáng hơn.")
    pc, ref_pc = metrics.get("avg_paragraph_chars") or 0, reference.get("avg_paragraph_chars") or 165
    if pc < ref_pc * 0.7:
        directives.append(
            f"Đoạn đang quá ngắn ({pc} ký tự, chuẩn ~{ref_pc}). GỘP đoạn liên tiếp cùng "
            f"cảnh/ý thành đoạn đầy đủ 120–220 ký tự.")
    elif pc > ref_pc * 1.35:
        directives.append(
            f"Đoạn đang quá dài ({pc} ký tự, chuẩn ~{ref_pc}). CHẺ thành đoạn 130–210 ký tự.")
    comma, ref_comma = metrics.get("comma_per_10k_chars") or 0, reference.get("comma_per_10k_chars") or 196
    if comma < ref_comma * 0.75:
        directives.append(
            f"Mật độ dấu phẩy thấp ({comma}/10k, chuẩn ~{ref_comma}). Thêm mệnh đề phụ "
            "nối bằng dấu phẩy: trạng ngữ thời gian/cảnh vật đầu câu, mệnh đề giải thích.")
    ss = metrics.get("short_sentence_ratio_lt10")
    ref_ss = reference.get("short_sentence_ratio_lt10")
    if ss is not None and ref_ss is not None and ss > max(0.30, ref_ss * 1.6):
        directives.append(
            f"Quá nhiều câu dưới 10 từ ({ss:.0%}, chuẩn ~{ref_ss:.0%}). Gộp hoặc kéo dài "
            "chúng; chỉ giữ câu ngắn cho khoảnh khắc chấn động.")
    vs = metrics.get("very_short_paragraph_ratio_lt60")
    ref_vs = reference.get("very_short_paragraph_ratio_lt60")
    if vs is not None and ref_vs is not None and vs > max(0.15, ref_vs * 2):
        directives.append(
            f"Quá nhiều đoạn dưới 60 ký tự ({vs:.0%}, chuẩn ~{ref_vs:.0%}). Gộp đoạn "
            "một-câu vào đoạn trước/sau trừ thoại đắt giá.")
    return directives


class StyleRewriteLoop:
    """Draft → measure → directive → rewrite → re-measure. Giữ best draft."""

    def __init__(self, reference: Dict[str, Any],
                 rewrite_fn: Callable[[str, List[str]], str],
                 target_fidelity: float = 90.0,
                 max_rounds: int = 2):
        """
        rewrite_fn(draft_text, directives) -> rewritten_text  (LLM call do caller inject)
        """
        self.reference = reference
        self.rewrite_fn = rewrite_fn
        self.target_fidelity = target_fidelity
        self.max_rounds = max_rounds

    def run(self, draft_text: str) -> Dict[str, Any]:
        history: List[Dict[str, Any]] = []
        best_text = draft_text
        best_metrics = analyze_text(draft_text)
        best_fid = fidelity(best_metrics, self.reference)

        for round_no in range(1, self.max_rounds + 1):
            # Chỉ tốn call khi fidelity THỰC SỤ dưới target. Directive lệch nhẹ
            # (văn VI hiện đại 15-22 từ/câu) không đáng một lần gọi LLM.
            if best_fid >= self.target_fidelity:
                break
            directives = style_directives(best_metrics, self.reference)
            try:
                candidate = self.rewrite_fn(best_text, directives)
            except Exception as e:
                history.append({"round": round_no, "error": str(e)})
                break
            if not candidate or len(candidate.split()) < 50:
                history.append({"round": round_no, "skipped": "empty/short rewrite"})
                continue
            cand_metrics = analyze_text(candidate)
            cand_fid = fidelity(cand_metrics, self.reference)
            improved = cand_fid > best_fid
            history.append({
                "round": round_no,
                "directives": directives,
                "fidelity_before": best_fid,
                "fidelity_after": cand_fid,
                "accepted": improved,
            })
            if improved:
                best_text, best_metrics, best_fid = candidate, cand_metrics, cand_fid
            else:
                break  # không cải thiện — dừng, giữ best

        return {
            "text": best_text,
            "metrics": best_metrics,
            "fidelity": best_fid,
            "passed": best_fid >= self.target_fidelity and not style_hard_fail(best_metrics),
            "rounds_used": len(history),
            "history": history,
        }


def style_hard_fail(metrics: Dict[str, Any]) -> bool:
    """Hard-band check đồng bộ với StyleFingerprintChecker."""
    bands = {
        "avg_sentence_words": (14, 45),
        "avg_paragraph_chars": (80, 300),
        "comma_per_10k_chars": (100, 320),
        "short_sentence_ratio_lt10": (0.0, 0.50),
        "very_short_paragraph_ratio_lt60": (0.0, 0.35),
    }
    for name, (lo, hi) in bands.items():
        v = metrics.get(name)
        if v is None:
            continue
        if not (lo <= v <= hi):
            return True
    return bool(metrics.get("forbidden_english_jargon"))
