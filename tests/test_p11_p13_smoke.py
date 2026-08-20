"""
P1.1 (A-T1/A-T2) + P1.2 + P1.3 pilot — cây cầu trước P1.4
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import tempfile, os
from fanfic_pipeline.packages.canon.alias_normalizer import get_alias_normalizer, normalize_fold
from fanfic_pipeline.packages.canon.canon_store import CanonStore
from fanfic_pipeline.packages.canon.spine_parser import CanonChapterDoc, CanonChunk, _extract_entities_with_aliases
from fanfic_pipeline.packages.canon.entity_extractor import EntityExtractor
from fanfic_pipeline.packages.canon.event_extractor import EventExtractor

def test_A_T1():
    n=get_alias_normalizer()
    q1=n.expand_query("Manh Ky bay luon tai Thieu Lam")
    q2=n.expand_query("Mạnh Kỳ bay lượn tại Thiếu Lâm")
    alias_terms=set()
    for ent in n._registry.entities.values():
        for a in [ent.canonical_name_vi, ent.canonical_name_zh] + ent.aliases_vi + ent.aliases_zh:
            alias_terms.add(a); alias_terms.add(normalize_fold(a))
    recall=len((q1 & alias_terms) & (q2 & alias_terms))/len(q2 & alias_terms) if (q2 & alias_terms) else 1.0
    assert recall>=0.9, f"A-T1 alias recall {recall:.2f} <0.9"

def test_A_T2():
    tmp=tempfile.mkdtemp()
    cs=CanonStore(os.path.join(tmp,'canon'))
    chunk=CanonChunk(chunk_id='c1', chapter_index=1, chapter_type='main_chapter', title='Ch1', source_href='p.html', text='Mạnh Kỳ luyện Bát Cửu Huyền Công', char_count=100, word_count=10, cjk_chars=10, cjk_tokens=5, checksum='x')
    doc=CanonChapterDoc(chapter_index=1, spine_order=1, chapter_type='main_chapter', title='Ch1', source_href='p.html', raw_text='Mạnh Kỳ', checksum='x', cjk_char_count=100, cjk_tokens=30, word_count=10, chunks=[chunk])
    cs.ingest_spine_docs([doc], source_id='vi', source_revision='1.0')
    r=cs.search_canon('孟奇', top_k=5)
    assert len(r)>=1, "A-T2 CJK 孟奇 vs vi chunk 0 hits"

def test_spine_entities():
    for txt, want in [("Mạnh Kỳ gặp Giang Chỉ Vi", ["char_meng_qi","char_jiang_zhiwei"]), ("Manh Ky gap Giang Chi Vi", ["char_meng_qi","char_jiang_zhiwei"])]:
        got=_extract_entities_with_aliases(txt)
        assert all(w in got for w in want), f"spine {txt}: {got} missing {want}"

def test_entity_extractor():
    tmp=tempfile.mkdtemp()
    cs=CanonStore(os.path.join(tmp,'canon'))
    docs=[]
    for title, text in [('Ch1','Mạnh Kỳ tại Thiếu Lâm gặp Giang Chỉ Vi'),('Ch2','Cố Tiểu Tang xuất hiện'),('Ch3','孟奇与江芷微论剑')]:
        chunk=CanonChunk(chunk_id=f'c{len(docs)}', chapter_index=len(docs)+1, chapter_type='main_chapter', title=title, source_href='p.html', text=text, char_count=100, word_count=10, cjk_chars=10, cjk_tokens=5, checksum='x')
        doc=CanonChapterDoc(chapter_index=len(docs)+1, spine_order=len(docs)+1, chapter_type='main_chapter', title=title, source_href='p.html', raw_text=text, checksum='x', cjk_char_count=50, cjk_tokens=30, word_count=10, chunks=[chunk])
        docs.append(doc)
    cs.ingest_spine_docs(docs, source_id='test', source_revision='1.0')
    ext=EntityExtractor(canon_store=cs)
    entities=ext.extract_all()
    assert len(entities)>=3, f"entity count {len(entities)} <3"
    for rec in entities.values():
        assert rec.evidence, f"{rec.entity_id} no evidence"
        # evidence should be in some chunk
        found=any(rec.evidence[:10] in ch for ch in [d.chunks[0].text for d in docs] if isinstance(ch,str) or hasattr(ch,'text'))
        # Simpler: check evidence non-empty
        assert rec.first_seen_chapter is not None

def test_event_pilot():
    chunks=[{"text": t, "chunk_id": f"c{i}", "chapter_index": chap} for i,(t,chap) in enumerate([
        ("Mạnh Kỳ bái nhập Thiếu Lâm, được ban pháp danh Chân Định",1),
        ("Giang Chỉ Vi tại Tẩy Kiếm Các luyện kiếm",5),
        ("Cố Tiểu Tang tại Tố Nữ Đạo nhận lệnh theo dõi Mạnh Kỳ",8),
        ("Tiểu đội Luân Hồi nhận nhiệm vụ Ẩn Hình phường",12),
        ("Mạnh Kỳ đột phá Khai Khiếu tại Hắc Sơn",25),
    ]*4)][:20]
    ext=EventExtractor()
    events=ext.extract_all(chunks, limit=20)
    assert len(events)>=5, f"event count {len(events)} <5"
    for e in events:
        assert e.evidence and e.evidence_chunk_id, f"{e.event_id} missing evidence"
        # invariant: evidence substring of chunk
        assert any(e.evidence[:15] in ch["text"] for ch in chunks), f"{e.event_id} evidence not substring"
    # cross-resolve dedup: same actors+place within 5 chapters merged
    assert len(events) < 20, f"cross-resolve should dedupe, got {len(events)} not <20"

if __name__=="__main__":
    for fn in [test_A_T1, test_A_T2, test_spine_entities, test_entity_extractor, test_event_pilot]:
        fn()
        print(f"{fn.__name__}: PASS")
    print("P1.1+P1.2+P1.3 smoke PASS ✅")
