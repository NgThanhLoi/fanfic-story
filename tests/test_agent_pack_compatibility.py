import pytest
from fanfic_pipeline.data.knowledge_pack_loader import KnowledgePackLoader
from fanfic_pipeline.core.context_builder import ContextCompiler
from fanfic_pipeline.packages.canon.canon_intelligence import CanonIntelligenceEngine
from fanfic_pipeline.core.models import CharacterVoice

def test_planner_writer_auditor_smooth_pack_compatibility():
    # 1. Nạp pack vào RAM
    pack = KnowledgePackLoader.load("nhat_the_chi_ton")
    assert pack is not None

    # 2. PLANNER: Lấy lộ trình 1410 chương & Grand Arcs
    arcs = pack.canonical_timeline["grand_arcs"]
    assert len(arcs) >= 7
    arc_1 = arcs[0]
    assert arc_1["mastermind"] == "Ma Phật An Nan"

    # 3. WRITER CONTEXT: Compile Writer Packet với đầy đủ Stage Voice & Epistemic Horizon
    cc = ContextCompiler()
    base_voice = CharacterVoice(
        character_id="meng_qi", name="Mạnh Kỳ", gender="Nam",
        personality_core="Mạnh Kỳ", dialogue_rhythm="Nhanh",
        moral_boundaries="Bạn bè", secret_motive="Lục Đạo"
    )
    packet = cc.compile_writer_packet(
        chapter_num=78,
        pov_character="Mạnh Kỳ",
        active_characters=["Mạnh Kỳ", "Giang Chỉ Vi"],
        full_state={"current_location": "Quảng trường Luân Hồi"},
        planner_ctx={"volume_title": "Quyển 1", "arc_title": "Ẩn Hình Phường"},
        canon_hits=[], memory_hits=[],
        voices={"Mạnh Kỳ": base_voice}
    )

    # Kiểm tra Writer Packet nhận diện mượt mà:
    assert "ĐẠI CHIẾN DỊCH CANON" in packet.arc_section
    assert "VÙNG CẤM TRI THỨC" in packet.character_lenses
    assert packet.sealed is True

    # 4. AUDITOR: Đối soát cảnh giới và điều cấm kỵ
    realms = pack.cultivation_mechanics["realms_26_tiers"]
    taboos = pack.cosmic_invariants["taboos"]
    assert len(realms) >= 19
    assert len(taboos) >= 4
