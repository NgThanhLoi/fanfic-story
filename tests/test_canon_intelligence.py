import pytest
from fanfic_pipeline.packages.canon.canon_intelligence import CanonIntelligenceEngine, GRAND_ARCS
from fanfic_pipeline.core.models import CharacterVoice
from fanfic_pipeline.core.context_builder import ContextCompiler

def test_grand_arcs_coverage():
    assert len(GRAND_ARCS) >= 7
    arc_ch10 = CanonIntelligenceEngine.get_arc_for_chapter(10)
    assert "Thiếu Lâm" in arc_ch10["title"]
    assert "Ma Phật" in arc_ch10["mastermind"]

    arc_ch550 = CanonIntelligenceEngine.get_arc_for_chapter(550)
    assert "Tô Tiên Sinh" in arc_ch550["title"]

def test_dynamic_voice_evolution_across_stages():
    base_voice = CharacterVoice(
        character_id="meng_qi",
        name="Mạnh Kỳ",
        gender="Nam",
        personality_core="Trang bức",
        dialogue_rhythm="Nhanh",
        moral_boundaries="Bảo vệ bạn bè",
        secret_motive="Chặt đứt Lục Đạo"
    )

    v_stage1 = CanonIntelligenceEngine.get_voice_for_chapter("meng_qi", 30, base_voice)
    assert "Tiểu Hòa Thượng" in v_stage1.personality_core

    v_stage2 = CanonIntelligenceEngine.get_voice_for_chapter("meng_qi", 120, base_voice)
    assert "Cuồng Đao" in v_stage2.personality_core

    v_stage3 = CanonIntelligenceEngine.get_voice_for_chapter("meng_qi", 550, base_voice)
    assert "Tô Tiên Sinh" in v_stage3.personality_core

def test_epistemic_time_locked_boundary():
    bound_early = CanonIntelligenceEngine.get_epistemic_boundary("meng_qi", 80)
    assert any("Ma Phật" in f for f in bound_early["forbidden"])

def test_context_compiler_injects_canon_intelligence():
    cc = ContextCompiler()
    base_voice = CharacterVoice(
        character_id="meng_qi",
        name="Mạnh Kỳ",
        gender="Nam",
        personality_core="Trang bức",
        dialogue_rhythm="Nhanh",
        moral_boundaries="Bảo vệ bạn bè",
        secret_motive="Chặt đứt Lục Đạo"
    )
    packet = cc.compile_writer_packet(
        chapter_num=120,
        pov_character="Mạnh Kỳ",
        active_characters=["Mạnh Kỳ"],
        full_state={"current_location": "Giang Hồ"},
        planner_ctx={"volume_title": "Quyển 1", "arc_title": "Nhân Bảng"},
        canon_hits=[],
        memory_hits=[],
        voices={"Mạnh Kỳ": base_voice}
    )
    assert "Cuồng Đao" in packet.character_lenses
    assert "ĐẠI CHIẾN DỊCH CANON" in packet.arc_section
    assert "VÙNG CẤM TRI THỨC" in packet.character_lenses
