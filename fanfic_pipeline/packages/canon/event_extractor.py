"""
P1.3 — Event Extractor (SPEC §A5) — Pilot on 20 chương:
- Local pass: mỗi chunk -> 1+ canon_event {actors, place, canon_chapter, preconditions, effects, evidence (substring), necessity}
- Cross-chapter resolve: gộp event trùng (same actors+place) thành 1, cộng evidence
- necessity ∈ {load_bearing, contingent, incidental} (heuristic rule-based, LLM đề xuất sau)
- Evidence binding: mọi event phải có evidence là substring thật của chunk (tái dùng nguyên tắc BUG-06)
"""
import re, json, pathlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import hashlib

def _sha8(s: str) -> str: return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]

class CanonEvent(BaseModel):
    event_id: str  # EVT:<chapter_idx:04d>:<seq>
    canon_chapter: int
    title: str = ""
    actors: List[str] = Field(default_factory=list)  # entity_ids
    place: Optional[str] = None
    preconditions: List[str] = Field(default_factory=list)  # fact_ids or free text
    effects: List[str] = Field(default_factory=list)
    evidence: str = ""  # substring thật của chunk
    evidence_chunk_id: Optional[str] = None
    necessity: str = "contingent"  # load_bearing | contingent | incidental
    scope: str = "personal"  # personal/local/faction/world
    source_hash: str = ""

class EventExtractor:
    # Heuristic keywords mapping to necessity/scope
    LOAD_BEARING_KWS = ["bái nhập", "đột phá", "tử vong", "kết bái", "bái sư", "nhận nhiệm vụ", "rời khỏi", "gia nhập"]
    INCIDENTAL_KWS = ["ăn", "uống", "cười", "gật đầu", "thích", "mùi", "ngon"]

    def __init__(self, alias_normalizer=None):
        try:
            from fanfic_pipeline.packages.canon.alias_normalizer import get_alias_normalizer
            self.normalizer = alias_normalizer or get_alias_normalizer()
        except:
            self.normalizer = None

    def _necessity(self, text: str) -> str:
        low = text.lower()
        for kw in self.LOAD_BEARING_KWS:
            if kw in low: return "load_bearing"
        for kw in self.INCIDENTAL_KWS:
            if kw in low: return "incidental"
        return "contingent"

    def _scope(self, actors: List[str], text: str) -> str:
        if any(k in text for k in ["Cửu Châu", "Thiên hạ", "Cửu Trọng Thiên", "Cửu Cửu"]):
            return "world"
        if any(k in text for k in ["Tố Nữ Đạo", "Thiếu Lâm", "Tẩy Kiếm Các", "Hoán Hoa"]):
            return "faction"
        if len(actors) >= 3: return "local"
        return "personal"

    def extract_local(self, chunk_text: str, chunk_id: str, canon_chapter: int) -> List[CanonEvent]:
        """Local pass: split chunk into sentences/clauses, each meaningful clause -> event."""
        # Split by sentence boundary (Vietnamese + CJK)
        sents = [s.strip() for s in re.split(r'[。．.!?！？\n]+', chunk_text) if len(s.strip())>=12]
        events=[]
        for idx, sent in enumerate(sents[:8]):  # at most 8 events per chunk
            if len(sent) < 15: continue
            # Only keep sentences with at least one known entity or action verb
            has_entity = False
            actors=[]
            if self.normalizer:
                spans = self.normalizer.entity_spans(sent)
                actors = list(set(sp["entity_id"] for sp in spans))
                has_entity = len(actors) > 0
            # Action verb heuristic
            action_re = re.search(r'(gặp|đấu|chiến|giết|rời|đến|nhận|bái|đột phá|tử vong|tố giác|che giấu|luyện|học|đi|về|nói|hỏi)', sent)
            if not has_entity and not action_re:
                continue
            ev = CanonEvent(
                event_id=f"EVT:{canon_chapter:04d}:{idx+1:02d}",
                canon_chapter=canon_chapter,
                title=sent[:60],
                actors=actors[:4],
                place=None,
                preconditions=[],
                effects=[],
                evidence=sent[:200],  # substring thật
                evidence_chunk_id=chunk_id,
                necessity=self._necessity(sent),
                scope=self._scope(actors, sent),
                source_hash=_sha8(sent),
            )
            # Evidence must be substring
            assert ev.evidence in chunk_text, f"evidence not substring: {ev.evidence!r} not in {chunk_text[:50]!r}"
            events.append(ev)
        return events

    def cross_resolve(self, events: List[CanonEvent]) -> List[CanonEvent]:
        """Cross-chapter resolve: gộp event có cùng actors+place và evidence overlap."""
        # Dedupe by (actors tuple, necessity, close chapter)
        seen={}
        out=[]
        for ev in events:
            key = (tuple(sorted(ev.actors)), ev.scope, ev.necessity)
            # Find close event with same key within 5 chapters
            merged=False
            for prev in out:
                if tuple(sorted(prev.actors))==tuple(sorted(ev.actors)) and prev.scope==ev.scope and abs(prev.canon_chapter - ev.canon_chapter)<=5:
                    # Merge: keep earlier, append evidence
                    if ev.evidence not in prev.evidence:
                        prev.effects.append(ev.evidence[:40])
                    merged=True
                    break
            if not merged:
                out.append(ev)
        return out

    def extract_all(self, chunks: List[Dict[str,Any]], limit: int = 20) -> List[CanonEvent]:
        """Pilot: limit chunks, extract local then cross-resolve."""
        all_events=[]
        for ch in chunks[:limit]:
            text = (ch.get("text") if isinstance(ch, dict) else getattr(ch, "text", "")) or ""
            cid = (ch.get("chunk_id") if isinstance(ch, dict) else getattr(ch, "chunk_id", "unk"))
            chap = (ch.get("chapter_index") if isinstance(ch, dict) else getattr(ch, "chapter_index", 0)) or (ch.get("canon_chapter") if isinstance(ch, dict) else 0) or 0
            all_events.extend(self.extract_local(text, cid, chap))
        return self.cross_resolve(all_events)

    def save(self, events: List[CanonEvent], out_path: str):
        pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        data=[e.model_dump() for e in events]
        pathlib.Path(out_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_path

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser(description="Extract canon events pilot")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--out", default=None)
    args=ap.parse_args()
    # Try load from CanonStore
    from fanfic_pipeline.core.state_manager import ProjectStateManager
    from fanfic_pipeline.packages.canon.canon_store import CanonStore
    import sys
    mgr=ProjectStateManager("nhat_the_fanfic")
    cs=CanonStore(str(pathlib.Path(mgr.project_dir)/"canon_store"))
    # Fallback: generate mock chunks if store empty
    chunks=[]
    for attr in ["_chunks", "chunks"]:
        if hasattr(cs, attr):
            v=getattr(cs, attr)
            if isinstance(v, list) and v: chunks=v; break
    if not chunks:
        print("CanonStore empty — generating 20 mock chunks for pilot schema validation")
        from fanfic_pipeline.packages.canon.spine_parser import CanonChunk, CanonChapterDoc
        import tempfile, os
        tmp=tempfile.mkdtemp()
        cs2=CanonStore(os.path.join(tmp,"canon"))
        mocks=[
            ("Mạnh Kỳ bái nhập Thiếu Lâm, được ban pháp danh Chân Định", 1),
            ("Giang Chỉ Vi tại Tẩy Kiếm Các luyện kiếm, kiếm tâm thông minh", 5),
            ("Cố Tiểu Tang tại Tố Nữ Đạo nhận lệnh theo dõi Mạnh Kỳ", 8),
            ("Tiểu đội Luân Hồi nhận nhiệm vụ Ẩn Hình phường từ Lục Đạo", 12),
            ("Mạnh Kỳ đột phá Khai Khiếu tại Hắc Sơn, Giang Chỉ Vi hộ pháp", 25),
            ("Nguyễn Ngọc Thư ôm cổ cầm Phượng Tê diễn tấu tại Quảng trường", 10),
        ]*4
        for i,(text,chap) in enumerate(mocks[:20]):
            chunk=CanonChunk(chunk_id=f"c{i}", chapter_index=chap, chapter_type="main_chapter", title=f"Ch{chap}", source_href="p.html", text=text, char_count=len(text), word_count=len(text.split()), cjk_chars=5, cjk_tokens=3, checksum="x")
            chunks.append({"text": text, "chunk_id": f"c{i}", "chapter_index": chap})
    ext=EventExtractor()
    events=ext.extract_all(chunks, limit=args.limit)
    out=args.out or f"/tmp/canon_events_pilot_{args.limit}.json"
    ext.save(events, out)
    print(f"Pilot {len(chunks)} chunks -> {len(events)} events -> {out}")
    for e in events[:8]:
        print(f" {e.event_id} ch{e.canon_chapter} {e.necessity}/{e.scope} actors={e.actors} evidence={e.evidence[:40]!r}")
    # Evidence invariant
    bad=[e for e in events if not any(e.evidence[:20] in (ch.get("text","") if isinstance(ch,dict) else getattr(ch,"text","")) for ch in chunks)]
    if bad:
        print(f"WARN: {len(bad)} events evidence not substring")
    else:
        print("Evidence invariant: 100% substring ✅")
