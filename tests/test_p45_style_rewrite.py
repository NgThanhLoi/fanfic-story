"""
P4.5 — Style Rewrite Loop test đối kháng.

- Directive phải chỉ đúng metric lệch + hướng lệch (câu ngắn → gộp; câu dài → chẻ)
- Loop dừng theo max_rounds; không tốn call khi đã đạt
- Không cải thiện ⇒ giữ best, dừng sớm
- LLM lỗi/empty ⇒ không crash, trả best gốc
- Fail-closed: vẫn FAIL sau loop ⇒ passed=False (audit gate chặn như thường)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fanfic_pipeline.packages.retrieval.style_rewrite import (
    StyleRewriteLoop, style_directives, style_hard_fail,
)
from fanfic_pipeline.packages.retrieval.style_profile import analyze_text, refingerprint, fidelity


@pytest.fixture(scope="module")
def fp():
    return refingerprint("fanfic_pipeline/data/nhat_the_chi_ton/vi_canon", 28, 43)


SHORT_TEXT = "\n\n".join([
    "Mạnh Kỳ rút đao. Hắn chém một nhát. Gió nổi lên. Lá rơi đầy sân.",
    "Vô Tâm né khéo. Hắn gật đầu khen. Mạnh Kỳ không nói gì. Hắn tiếp tục luyện.",
    "Trời tối dần. Hai người dừng nghỉ. Hắn ngồi xuống đá. Mồ hôi rơi lã chã.",
])

LONG_SENTENCE_TEXT = (
    "Mạnh Kỳ đứng giữa sân chùa cổ kính với thanh đao sắt cũ kỹ trong tay mà lặng "
    "nhìn bầu trời chiều tím thẫm đang từ từ nhuộm cả khoảng sân gạch rêu phong "
    "thấm đẫm hơi nước muối biển xa xăm nào đó không rõ nguồn cội từ đâu mang đến, "
    "trong đầu hắn hiện về những ngày tháng tu hành khổ hạnh nơi thiền môn cùng "
    "tiếng chuông chiều vẳng vọng xa xăm buồn bã qua từng lớp mây trắng trôi.\n"
) * 3


class TestDirectives:
    def test_short_sentence_directive(self):
        m = analyze_text(SHORT_TEXT)
        ds = style_directives(m, {"avg_sentence_words": 27})
        assert any("quá ngắn" in d for d in ds)

    def test_long_sentence_directive(self):
        m = analyze_text(LONG_SENTENCE_TEXT)
        ds = style_directives(m, {"avg_sentence_words": 27})
        assert any("quá dài" in d for d in ds)

    def test_no_directive_when_in_band(self):
        # metrics nằm trong dung sai ±25% ⇒ không directive
        m = {"avg_sentence_words": 25, "avg_paragraph_chars": 160,
             "comma_per_10k_chars": 190, "short_sentence_ratio_lt10": 0.2,
             "very_short_paragraph_ratio_lt60": 0.08}
        assert style_directives(m, {"avg_sentence_words": 27,
                                    "avg_paragraph_chars": 165,
                                    "comma_per_10k_chars": 196}) == []


class TestLoop:
    def test_stops_at_max_rounds(self, fp):
        calls = []
        def rewrite(text, directives):
            calls.append(directives)
            return text + " thêm"  # không cải thiện thật
        loop = StyleRewriteLoop(fp, rewrite, target_fidelity=99, max_rounds=3)
        out = loop.run(SHORT_TEXT)
        assert len(calls) <= 3
        assert out["rounds_used"] <= 3

    def test_keeps_best_on_no_improvement(self, fp):
        """Rewrite tệ hơn ⇒ giữ bản gốc, dừng sớm."""
        def worse(text, directives):
            return "Ngắn. Quá ngắn. Rất ngắn." * 10
        loop = StyleRewriteLoop(fp, worse, max_rounds=2)
        base_fid = fidelity(analyze_text(SHORT_TEXT), fp)
        out = loop.run(SHORT_TEXT)
        assert out["fidelity"] <= base_fid + 0.01
        assert out["text"] == SHORT_TEXT or out["history"][-1]["accepted"] is False

    def test_accepts_improvement(self, fp):
        """Rewrite tốt hơn ⇒ accept."""
        good = (
            "Mạnh Kỳ đứng giữa sân chùa, tay siết nhẹ chuôi đao sau lưng, mắt nhìn "
            "về phía chân trời xa xăm nơi mây trắng vẫn lững lờ trôi qua từng lớp "
            "núi trùng điệp phía xa, lòng hắn bình thản lạ thường.\n"
            "Võ tăng Vô Tâm bước ra từ bóng cây cổ thụ, hai tay chắp trước ngực, "
            "ánh mắt bình thản như mặt hồ thu không gợn sóng, chậm rãi gật đầu thừa "
            "nhận đao pháp của Mạnh Kỳ đã có chút hình hài riêng đáng để ghi nhớ.\n"
            "Hai người đối luyện đến canh khuya mới dừng lại nghỉ ngơi bên bờ suối "
            "nhỏ, tiếng nước chảy róc rách hòa cùng tiếng gió rì rào qua rặng tre "
            "xanh, mồ hôi trên trán Mạnh Kỳ rơi xuống đá, thấm đẫm rồi khô dần.")
        def better(text, directives):
            return good
        loop = StyleRewriteLoop(fp, better, max_rounds=1)
        out = loop.run(SHORT_TEXT)
        assert out["text"] == good
        assert out["history"][0]["accepted"] is True

    def test_llm_error_returns_original(self, fp):
        def broken(text, directives):
            raise RuntimeError("LLM down")
        loop = StyleRewriteLoop(fp, broken, max_rounds=2)
        out = loop.run(SHORT_TEXT)
        assert out["text"] == SHORT_TEXT
        assert any("error" in h for h in out["history"])

    def test_empty_rewrite_skipped(self, fp):
        def empty(text, directives):
            return ""
        loop = StyleRewriteLoop(fp, empty, max_rounds=1)
        out = loop.run(SHORT_TEXT)
        assert out["text"] == SHORT_TEXT

    def test_no_call_when_already_passing(self, fp):
        called = []
        def rewrite(text, directives):
            called.append(1)
            return text
        loop = StyleRewriteLoop(fp, rewrite, target_fidelity=75)
        # văn câu ngắn vừa phải — fidelity cao, không directive lệch band
        good = "\n\n".join([
            "Mạnh Kỳ rời Thiếu Lâm đã nửa tháng, mỗi sáng lại luyện đao bên suối, "
            "mồ hôi thấm ướt lưng áo. Võ tăng Vô Tâm đứng xem từ xa, thỉnh thoảng "
            "gật đầu nhận xét vài câu.",
            "Đao pháp của hắn chưa mượt, nhưng lực đạo chắc tay hơn xưa nhiều. "
            "Một đường chém xuống, gió cắt qua lá tre rơi rụng. Vô Tâm vỗ tay khen.",
            "Hai người đối luyện đến canh khuya mới nghỉ. Trăng lên đỉnh núi, sương "
            "xuống dày. Mạnh Kỳ ngồi lau đao, tâm trí vẫn còn vương vấn chiêu thức.",
        ])
        out = loop.run(good)
        assert not called, "đã đạt target mà vẫn gọi LLM = phí token"

    def test_fail_closed_when_still_failing(self, fp):
        """Sau loop vẫn hard-fail ⇒ passed=False cho audit gate chặn."""
        def useless(text, directives):
            return text
        loop = StyleRewriteLoop(fp, useless, target_fidelity=90, max_rounds=1)
        out = loop.run("Quá ngắn. Vẫn ngắn. Cực ngắn.")
        assert out["passed"] is False


class TestHardFail:
    def test_english_jargon_is_hard_fail(self):
        m = analyze_text("The baseline workflow executed with maximum efficiency. " * 8)
        assert style_hard_fail(m)

    def test_clean_vi_not_hard_fail(self, fp):
        m = analyze_text(
            "Mạnh Kỳ đứng giữa sân chùa, tay siết nhẹ chuôi đao sau lưng, mắt nhìn "
            "về phía chân trời xa xăm nơi mây trắng vẫn lững lờ trôi qua từng lớp "
            "núi trùng điệp phía xa, lòng hắn bình thản lạ thường.")
        assert not style_hard_fail(m)
