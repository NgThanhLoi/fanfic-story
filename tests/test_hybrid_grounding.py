import pytest, tempfile, os
from fanfic_pipeline.packages.canon.canon_store import CanonStore
from fanfic_pipeline.packages.enrichment.enrichment_store import EnrichmentStore
from fanfic_pipeline.packages.enrichment.topic_scanner import TopicDeepScanner

def test_topic_deep_scanner_end_to_end():
    tmp_dir = tempfile.mkdtemp()
    cs = CanonStore(os.path.join(tmp_dir, "canon"))
    cs.ingest_chunks([
        {
            "chunk_id": "chunk_001",
            "text": "Mạnh Kỳ tiến vào Thiền Định Súc Khí, sau đó tu luyện Như Lai Thần Chưởng tại Thiếu Lâm Tự.",
            "chapter_index": 5,
            "title": "Chương 5",
            "source_id": "epub_test"
        }
    ])

    es = EnrichmentStore(os.path.join(tmp_dir, "enrichment.db"))
    scanner = TopicDeepScanner(cs, es)
    stats = scanner.scan_all_topics()

    assert stats["realms"] >= 1
    assert stats["martial_arts"] >= 1
    assert stats["factions"] >= 1

    entities = es.query_all_entities()
    assert any(e.canonical_name == "Như Lai Thần Chưởng" for e in entities)


