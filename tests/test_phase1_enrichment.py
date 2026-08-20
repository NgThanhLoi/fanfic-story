"""
Unit & Integration Tests for Phase 1 (Enrichment Pipeline & Knowledge Base).
"""
import os, sys, pathlib, tempfile, pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fanfic_pipeline.packages.enrichment.enrichment_store import (
    EnrichmentStore, EnrichedEntity, EnrichedRelationship, EnrichedCausalLink, EpistemicRecord, ArcSummaryRecord
)
from fanfic_pipeline.packages.enrichment.evidence_validator import EvidenceValidator
from fanfic_pipeline.packages.enrichment.structural_extractor import StructuralExtractor
from fanfic_pipeline.packages.enrichment.semantic_extractor import SemanticExtractor
from fanfic_pipeline.packages.enrichment.checkpoint import EnrichmentCheckpoint
from fanfic_pipeline.packages.enrichment.batch_orchestrator import BatchOrchestrator
from fanfic_pipeline.packages.canon.power_ladder import rank_of, plausible, can_fly
from fanfic_pipeline.packages.canon.canon_exam import CanonExam
from fanfic_pipeline.data.story_bible_generator import generate_macro_bible_v2
from fanfic_pipeline.packages.canon.spine_parser import CanonChunk

def test_P1_T1_enrichment_store_crud():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test_enrichment.db")
    store = EnrichmentStore(db_path)

    # 1. Add entity
    ent = EnrichedEntity(
        id="ENT:char:meng_qi", canonical_name="Mạnh Kỳ",
        aliases=["Chân Định", "Cuồng Đao Tô Mạnh"], first_seen_chapter=1,
        mention_count=5, entity_type="character", evidence="Mạnh Kỳ nhìn vào gương đồng",
        source_chapter=1, confidence=1.0
    )
    store.add_entities([ent])
    assert store.stats()["entities"] == 1

    # Query by alias
    queried = store.query_entity("Chân Định")
    assert queried is not None
    assert queried.canonical_name == "Mạnh Kỳ"

    # Upsert with new alias and lower first_seen
    ent2 = EnrichedEntity(
        id="ENT:char:meng_qi", canonical_name="Mạnh Kỳ",
        aliases=["Lôi Đao"], first_seen_chapter=1,
        mention_count=2, entity_type="character"
    )
    store.add_entities([ent2])
    queried_again = store.query_entity("Lôi Đao")
    assert queried_again is not None
    assert "Cuồng Đao Tô Mạnh" in queried_again.aliases
    assert queried_again.mention_count == 7

def test_P1_T2_evidence_validator():
    validator = EvidenceValidator(min_length=10)
    chunks = [
        {"chunk_id": "c001", "text": "Mạnh Kỳ đứng trước Đại Hùng Bảo Điện của Thiếu Lâm Tự."},
        {"chunk_id": "c002", "text": "Giang Chỉ Vi mỉm cười, rút trường kiếm Lạc Hồng."}
    ]

    # Valid substring
    record_valid = EnrichedEntity(
        id="ENT:1", canonical_name="Mạnh Kỳ", aliases=[],
        evidence="Đại Hùng Bảo Điện của Thiếu Lâm Tự"
    )
    ok, cid = validator.validate(record_valid, chunks)
    assert ok is True
    assert cid == "c001"

    # Invalid substring (hallucinated)
    record_fake = EnrichedEntity(
        id="ENT:2", canonical_name="Fake", aliases=[],
        evidence="Một câu thoại hoàn toàn bịa đặt không có thật"
    )
    ok_fake, reason = validator.validate(record_fake, chunks)
    assert ok_fake is False
    assert "not found" in reason

def test_P1_T3_structural_extractor():
    extractor = StructuralExtractor()
    chunks = [
        CanonChunk(
            chunk_id="c1", chapter_index=1, chapter_type="main_chapter",
            title="Ch1", source_href="p1.html",
            text="Mạnh Kỳ tại Thiếu Lâm Tự tu luyện Bát Cửu Huyền Công, đột phá Khai Khiếu cảnh giới.",
            char_count=80, word_count=15, cjk_chars=0, cjk_tokens=0, checksum="abc"
        )
    ]
    entities = extractor.extract_from_chunks(chunks, current_chapter=1)
    e_types = {e.entity_type for e in entities}
    assert "character" in e_types
    assert "location" in e_types
    assert "technique" in e_types
    assert "realm" in e_types

def test_P1_T4_semantic_extractor_heuristic():
    extractor = SemanticExtractor(model_invoker=None)
    known = [
        EnrichedEntity(id="ENT:char:meng_qi", canonical_name="Mạnh Kỳ", aliases=["Chân Định"], entity_type="character"),
        EnrichedEntity(id="ENT:char:giang_chi_vi", canonical_name="Giang Chỉ Vi", aliases=[], entity_type="character")
    ]
    chunks = [
        {"text": "Mạnh Kỳ cùng Giang Chỉ Vi kề vai chiến đấu chống lại sát thủ Ẩn Hình Phường.", "chapter_index": 1}
    ]
    discovered, rels, causal, epistemic, summary = extractor.extract_from_window(1, 1, 30, chunks, known)
    assert len(rels) >= 1
    assert rels[0].type in ("ally", "adversary")
    assert summary.window_id == 1


def test_P1_T5_power_ladder_expansion():
    # Rank order
    r_truc_co = rank_of("Trúc Cơ")
    r_khai_khieu = rank_of("Khai Khiếu (Sơ kỳ - 1-4 Khiếu)")
    r_ngoai_canh = rank_of("Ngoại Cảnh (Nhất Trọng Thiên)")
    r_phap_than = rank_of("Pháp Thân (Địa Tiên)")
    r_bi_ngan = rank_of("Bỉ Ngạn Cảnh")

    assert 0 <= r_truc_co < r_khai_khieu < r_ngoai_canh < r_phap_than < r_bi_ngan

    # Flight capability
    assert can_fly("Khai Khiếu cửu khiếu") is False
    assert can_fly("Ngoại Cảnh (Thiên Nhân Hợp Nhất)") is True
    assert can_fly("Pháp Thân") is True

    # Plausibility
    assert plausible("Khai Khiếu -> Pháp Thân", elapsed_days=3) is False
    assert plausible("Khai Khiếu -> Ngoại Cảnh", elapsed_days=180) is True

def test_P1_T6_canon_exam_gate():
    tmp_dir = tempfile.mkdtemp()
    store = EnrichmentStore(os.path.join(tmp_dir, "enrichment.db"))
    store.add_entities([
        EnrichedEntity(id="ENT:1", canonical_name="Mạnh Kỳ", aliases=[], first_seen_chapter=1, entity_type="character")
    ])

    exam = CanonExam(enrichment_store=store)
    qs = exam.generate(n=10)
    assert len(qs) == 10

    # Gate without answers -> Fail (not submitted)
    gate_empty = exam.gate(answers=None, questions=qs)
    assert gate_empty["passed"] is False

    # Gate with 100% correct answers -> Pass
    correct_answers = {q.qid: q.answer for q in qs}
    gate_pass = exam.gate(answers=correct_answers, questions=qs)
    assert gate_pass["passed"] is True
    assert gate_pass["overall"] == 100.0

def test_P1_T7_story_bible_generator():
    summaries = [
        ArcSummaryRecord(window_id=1, start_chapter=1, end_chapter=30, summary_text="Tân thủ thử luyện"),
        ArcSummaryRecord(window_id=2, start_chapter=31, end_chapter=60, summary_text="Giang hồ sơ xuất")
    ]
    bible = generate_macro_bible_v2(summaries, total_chapters=1000)
    assert bible["version"] == "2.0"
    assert len(bible["volumes"]) == 4
    assert len(bible["arcs"]) >= 20

def test_P1_T8_llm_discovery_and_registry_feedback():
    from fanfic_pipeline.packages.enrichment.enrichment_store import EnrichmentStore, EnrichedEntity
    from fanfic_pipeline.packages.enrichment.evidence_validator import EvidenceValidator
    from fanfic_pipeline.packages.canon.alias_registry import AliasRegistry, CanonicalEntity
    from fanfic_pipeline.packages.enrichment.structural_extractor import StructuralExtractor
    import tempfile, os

    # 1. Mock chunk containing a new entity not in default registry
    chunk = {"chunk_id": "c100", "text": "Huyền Tâm đại sư xuất thủ thi triển La Hán Quyền đánh lui địch nhân.", "chapter_index": 5}
    chunks = [chunk]

    # 2. Structural scan before LLM discovery: Huyền Tâm not known yet
    extractor = StructuralExtractor()
    before_ents = [e.canonical_name for e in extractor.extract_from_chunks(chunks, current_chapter=5)]
    assert "Huyền Tâm" not in before_ents

    # 3. LLM discovers new entity with valid evidence
    discovered_ent = EnrichedEntity(
        id="ENT:char:huyen_tam",
        canonical_name="Huyền Tâm",
        aliases=["Huyền Tâm đại sư"],
        first_seen_chapter=5,
        entity_type="character",
        evidence="Huyền Tâm đại sư xuất thủ",
        source_chapter=5
    )

    # 4. Validate evidence
    validator = EvidenceValidator()
    ok, _ = validator.validate(discovered_ent, chunks)
    assert ok is True

    # 5. Register into AliasRegistry
    registry = extractor.normalizer._registry
    registry.register_entity(
        CanonicalEntity(
            entity_id=discovered_ent.id,
            canonical_name_vi=discovered_ent.canonical_name,
            aliases_vi=discovered_ent.aliases,
            entity_type="character"
        ),
        provenance="llm_discovery"
    )

    # 6. Structural scan AFTER registration: now detected at 0 tokens!
    after_ents = [e.canonical_name for e in extractor.extract_from_chunks(chunks, current_chapter=5)]
    assert "Huyền Tâm" in after_ents
