import pytest
from fanfic_pipeline.data.knowledge_pack_loader import KnowledgePackLoader, CanonKnowledgePack

def test_master_lore_pack_integrity():
    pack = KnowledgePackLoader.load("nhat_the_chi_ton")
    assert isinstance(pack, CanonKnowledgePack)
    assert pack.manifest["fandom_id"] == "nhat_the_chi_ton"
    assert pack.manifest["total_canon_chapters"] == 1409

    # 1. Geography
    assert "Chân Thực Giới" in pack.world_geography["realms"]
    assert "Khai Khiếu (1-9 khiếu)" in pack.world_geography["travel_mechanics"]

    # 2. Cultivation
    assert len(pack.cultivation_mechanics["realms_26_tiers"]) == 26
    assert pack.cultivation_mechanics["realms_26_tiers"][0]["name"] == "Bách Nhật Trúc Cơ"

    # 3. Factions & Conspiracies
    assert "Thiếu Lâm Tự" in pack.factions_and_conspiracies["chinh_dao"]
    assert "Ma Phật An Nan" in pack.factions_and_conspiracies["masterminds"]

    # 4. Timeline
    assert len(pack.canonical_timeline["grand_arcs"]) >= 7
    assert pack.canonical_timeline["grand_arcs"][0]["mastermind"] == "Ma Phật An Nan"

    # 5. Character dossiers
    chars = pack.character_dossiers["characters"]
    assert "meng_qi" in chars
    assert len(chars["meng_qi"]["stages"]) == 4

    # 6. Cosmic invariants
    assert len(pack.cosmic_invariants["taboos"]) >= 3
