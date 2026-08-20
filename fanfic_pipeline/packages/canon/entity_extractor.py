"""
P1.2 — Entity Extractor (SPEC §A3):
- Quét canon_chunks (hoặc CanonStore authority) + dùng alias_normalizer để extract
- Mỗi entity có first_seen_chapter, aliases[], evidence (substring thật của chunk)
- Dedupe, evidence binding

Run standalone: python packages/canon/entity_extractor.py --project nhat_the_fanfic
Also importable: EntityExtractor(canon_store).extract_all()
"""
import re, json, pathlib, unicodedata
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field

class CanonEntityRecord(BaseModel):
    entity_id: str
    entity_type: str  # character, faction, location, item, technique, realm
    canonical_name_vi: str
    canonical_name_zh: str = ""
    aliases: List[str] = Field(default_factory=list)
    first_seen_chapter: Optional[int] = None
    first_seen_chunk: Optional[str] = None
    evidence: str = ""  # substring thật của chunk text
    evidence_chunk_id: Optional[str] = None
    mention_count: int = 0
    chapters: List[int] = Field(default_factory=list)

def strip_diacritics(s: str) -> str:
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('Đ','D').replace('đ','d')
    return s

def normalize_fold(s: str) -> str:
    return strip_diacritics(s.lower().strip())

class EntityExtractor:
    def __init__(self, canon_store=None, project_dir: Optional[str] = None):
        self.canon_store = canon_store
        self.project_dir = project_dir
        # Reuse alias_normalizer's registry + fold index for consistent alias handling
        from fanfic_pipeline.packages.canon.alias_normalizer import get_alias_normalizer
        self.normalizer = get_alias_normalizer()
        # Build alias -> entity_id map (folded)
        self.fold_to_eid: Dict[str, str] = {}
        # Also keep original alias -> eid for exact CJK
        self.exact_alias_to_eid: Dict[str, str] = {}
        for entry in self.normalizer._registry.alias_entries:
            fold = normalize_fold(entry.alias)
            if fold not in self.fold_to_eid:
                self.fold_to_eid[fold] = entry.entity_id
            if entry.alias not in self.exact_alias_to_eid:
                self.exact_alias_to_eid[entry.alias] = entry.entity_id

    def _chunks(self) -> List[Dict[str,Any]]:
        """Lấy chunks từ CanonStore hoặc fallback scan storage."""
        chunks=[]
        if self.canon_store is not None:
            # Try new API
            for attr in ["chunks", "_chunks", "get_chunks", "list_chunks"]:
                if hasattr(self.canon_store, attr):
                    val = getattr(self.canon_store, attr)
                    if callable(val):
                        try: val = val()
                        except: continue
                    if isinstance(val, list) and val:
                        chunks = val
                        break
                    if isinstance(val, dict) and val:
                        chunks = list(val.values())
                        break
            # Also try authority json
            if not chunks:
                try:
                    from pathlib import Path
                    p = Path(getattr(self.canon_store, 'canon_dir', '') or getattr(self.canon_store, 'storage_path', '') or '')
                    for name in ["canon_chunks.json", "authority/canon_chunks.json", "authority/canon_spans.json"]:
                        fp = p / name
                        if fp.exists():
                            data = json.loads(fp.read_text(encoding="utf-8"))
                            if isinstance(data, list) and data: chunks = data; break
                            if isinstance(data, dict) and data: chunks = list(data.values()); break
                except: pass
        # Fallback: scan project_dir
        if not chunks and self.project_dir:
            for p in pathlib.Path(self.project_dir).rglob("canon_chunks.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(data, list) and len(data)>len(chunks): chunks=data
                    elif isinstance(data, dict) and len(data)>len(chunks): chunks=list(data.values())
                except: pass
        return chunks

    def extract_all(self, chunks: Optional[List[Dict]]=None) -> Dict[str, CanonEntityRecord]:
        """
        Quét tất cả chunks, trả về entity_id -> CanonEntityRecord.
        Mỗi record có evidence là substring thật từ chunk đầu tiên gặp.
        """
        if chunks is None:
            chunks = self._chunks()
        # bucket: entity_id -> {first_seen_chapter, evidence, chunk_id, chapters set, count}
        bucket: Dict[str, Dict[str,Any]] = {}
        for ch in chunks:
            text = (ch.get("text") if isinstance(ch, dict) else getattr(ch, "text", "")) or (ch.get("content") if isinstance(ch, dict) else getattr(ch, "content", "")) or getattr(ch, "full_text", "") or ""
            if not text: continue
            chunk_id = (ch.get("chunk_id") if isinstance(ch, dict) else getattr(ch, "chunk_id", None)) or (ch.get("id") if isinstance(ch, dict) else getattr(ch, "id", None)) or getattr(ch, "source_chunk_id", None) or "unknown"
            chap = (ch.get("chapter_index") if isinstance(ch, dict) else getattr(ch, "chapter_index", None)) or (ch.get("chapter") if isinstance(ch, dict) else getattr(ch, "chapter", None)) or getattr(ch, "canon_chapter", None) or getattr(ch, "spine_order", None) or 0
            # Use normalizer entity_spans (fold-aware)
            spans = self.normalizer.entity_spans(text)
            for sp in spans:
                eid = sp["entity_id"]
                if eid not in bucket:
                    bucket[eid] = {"first_seen_chapter": chap, "first_seen_chunk": chunk_id, "evidence": text[sp["start"]:sp["end"]+20].strip()[:80] if sp["start"]>=0 else text[:80], "chapters": set([chap]), "count": 1, "chunk_id": chunk_id}
                    # Fix evidence to be substring
                    # Find actual alias in text window
                    alias = sp.get("alias","")
                    if alias and alias in text:
                        idx=text.find(alias)
                        bucket[eid]["evidence"] = text[max(0,idx-10): idx+len(alias)+20].strip()
                else:
                    b=bucket[eid]
                    if chap < b["first_seen_chapter"] or b["first_seen_chapter"] in (0, None):
                        b["first_seen_chapter"] = chap
                        b["first_seen_chunk"] = chunk_id
                        alias = sp.get("alias","")
                        if alias and alias in text:
                            idx=text.find(alias)
                            b["evidence"] = text[max(0,idx-10): idx+len(alias)+20].strip()
                    b["chapters"].add(chap)
                    b["count"] += 1
            # CJK direct (entity_spans already covers via normalizer's alias_index which includes CJK, but double ensure)
            for cjk in ["孟奇","江芷微","顾小桑","齐正言","阮玉书"]:
                if cjk in text:
                    # Map to known eid if not already via spans
                    eid_map={"孟奇":"char_meng_qi","江芷微":"char_jiang_zhiwei","顾小桑":"char_gu_xiaosang","齐正言":"char_qi_zhengyan","阮玉书":"char_ruan_yushu"}
                    eid=eid_map.get(cjk)
                    if eid and eid not in [sp["entity_id"] for sp in spans]:
                        if eid not in bucket:
                            idx=text.find(cjk)
                            bucket[eid]={"first_seen_chapter": chap, "first_seen_chunk": chunk_id, "evidence": text[max(0,idx-10):idx+len(cjk)+20].strip(), "chapters": set([chap]), "count": 1, "chunk_id": chunk_id}
                        else:
                            bucket[eid]["chapters"].add(chap); bucket[eid]["count"]+=1

        # Convert to CanonEntityRecord
        out: Dict[str, CanonEntityRecord] = {}
        for eid, info in bucket.items():
            ent = self.normalizer._registry.entities.get(eid)
            if not ent:
                continue
            # evidence must be substring of chunk text — verify
            # Find the actual chunk text for evidence chunk
            chunk_text = ""
            for ch in chunks:
                cid = ch.get("chunk_id") if isinstance(ch, dict) else getattr(ch, "chunk_id", None)
                iid = ch.get("id") if isinstance(ch, dict) else getattr(ch, "id", None)
                if (cid==info["first_seen_chunk"] or iid==info["first_seen_chunk"]):
                    chunk_text = (ch.get("text") if isinstance(ch, dict) else getattr(ch, "text", "")) or (ch.get("content") if isinstance(ch, dict) else getattr(ch, "content", "")) or ""
                    break
            if not chunk_text:
                chunk_text = info["evidence"]
            # Ensure evidence substring
            ev = info["evidence"]
            if ev not in chunk_text and chunk_text:
                # Trim to actual alias if possible
                ev = chunk_text[:60]
            aliases=[]
            for a in ent.aliases_vi + ent.aliases_zh:
                if a != ent.canonical_name_vi and a != ent.canonical_name_zh:
                    aliases.append(a)
            out[eid] = CanonEntityRecord(
                entity_id=eid,
                entity_type=ent.entity_type,
                canonical_name_vi=ent.canonical_name_vi,
                canonical_name_zh=ent.canonical_name_zh,
                aliases=aliases,
                first_seen_chapter=info["first_seen_chapter"],
                first_seen_chunk=info["first_seen_chunk"],
                evidence=ev,
                evidence_chunk_id=info["first_seen_chunk"],
                mention_count=info["count"],
                chapters=sorted(list(info["chapters"])),
            )
        return out

    def save(self, entities: Dict[str, CanonEntityRecord], out_path: str):
        pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        data={eid: rec.model_dump() for eid, rec in entities.items()}
        pathlib.Path(out_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_path

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser(description="Extract entities from canon")
    ap.add_argument("--project", default="nhat_the_fanfic")
    ap.add_argument("--out", default=None)
    ap.add_argument("--base-dir", default=None)
    args=ap.parse_args()
    # Try to load CanonStore
    from fanfic_pipeline.core.state_manager import ProjectStateManager
    mgr=ProjectStateManager(args.project, base_dir=args.base_dir)
    canon_dir = pathlib.Path(mgr.project_dir)/"canon_store"
    from fanfic_pipeline.packages.canon.canon_store import CanonStore
    cs=CanonStore(str(canon_dir))
    ext=EntityExtractor(canon_store=cs, project_dir=mgr.project_dir)
    entities=ext.extract_all()
    out=args.out or str(pathlib.Path(mgr.project_dir)/"canon"/"entities.json")
    ext.save(entities, out)
    print(f"Extracted {len(entities)} entities -> {out}")
    for eid, rec in list(entities.items())[:10]:
        print(f" {eid}: {rec.canonical_name_vi} ({rec.canonical_name_zh}) first_seen_ch={rec.first_seen_chapter} evidence={rec.evidence[:40]!r}")

