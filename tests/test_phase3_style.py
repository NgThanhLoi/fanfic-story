import pytest
from fanfic_pipeline.packages.style.scene_classifier import classify_scene
from fanfic_pipeline.packages.style.tone_modifier import get_dynamic_style_contract
from fanfic_pipeline.packages.style.character_voice_arc import get_voice_dynamics
from fanfic_pipeline.packages.style.metrics import analyze_prose_metrics
from fanfic_pipeline.core.context_builder import ContextCompiler

def test_P3_T1_scene_classifier():
    assert classify_scene("Trận quyết đấu đao kiếm sinh tử giữa hai cao thủ") == "combat"
    assert classify_scene("Mạnh Kỳ vừa uống rượu vừa cười trêu chọc đồng đội") == "banter"
    assert classify_scene("Tĩnh tọa bế quan đả tọa đột phá khai khiếu") == "cultivation"
    assert classify_scene("Truy tìm manh mối chân tướng hung thủ") == "deduction"

def test_P3_T2_tone_modifier():
    contract_combat = get_dynamic_style_contract("combat")
    assert "COMBAT" in contract_combat
    assert "đao phong kiếm khí" in contract_combat

    contract_banter = get_dynamic_style_contract("banter")
    assert "BANTER" in contract_banter
    assert "dí dỏm" in contract_banter

def test_P3_T3_character_voice_dynamics():
    vd = get_voice_dynamics("Mạnh Kỳ", "Giang Chỉ Vi", intimacy_level=7)
    assert vd.character == "Mạnh Kỳ"
    assert vd.intimacy_with == "Giang Chỉ Vi"
    assert vd.intimacy_level == 7
    assert len(vd.combat_tone) > 5
    assert len(vd.banter_tone) > 5

def test_P3_T4_prose_metrics():
    sample = '"Đao kiếm vô tình!" Mạnh Kỳ hét lớn.\nGiang Chỉ Vi mỉm cười rút kiếm.\nKhông gian rung chuyển dữ dội.'
    m = analyze_prose_metrics(sample)
    assert m["word_count"] > 10
    assert m["dialogue_ratio"] > 0.0

def test_P3_T5_context_compiler_style_integration():
    compiler = ContextCompiler()
    packet = compiler.compile_writer_packet(
        chapter_num=5,
        pov_character="Mạnh Kỳ",
        active_characters=["Mạnh Kỳ", "Giang Chỉ Vi"],
        full_state={"current_location": "Thiếu Lâm Tự", "character_realms": {}},
        planner_ctx={"arc_title": "Quyết chiến Ẩn Hình Phường"},
        canon_hits=[],
        memory_hits=[],
        voices={},
        author_instruction="Trận giao đấu đao kiếm kịch liệt với sát thủ"
    )
    assert "[PHONG CÁCH PHÂN CẢNH (COMBAT)]" in packet.style_contract
    assert "[KHẨU KHÍ QUAN HỆ" in packet.character_lenses
