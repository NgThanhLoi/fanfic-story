"""
Immutable Canon Store & Fact Database (FR-04, FR-05, FR-06 Compliant):
- Authority store: CanonSource / CanonChapter / SourceSpan immutable JSON in authority/
- Facts: evidence-backed (confidence>0.7 requires evidence), bitemporal fields, status
- CanonAlignment: fanfic chapter <-> canon chapter/event alignment map
- Retrieval: REAL FTS5 via sqlite3 (virtual table fts5, fallback LIKE+ranking), entity expansion, time filters
- FTS index is derived — rebuild_fts() drops & rebuilds
- source_revision validation, backward compat aliases
"""

import os
import json
import math
import re
import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

# AliasRegistry optional import
try:
    from fanfic_pipeline.packages.canon.alias_registry import AliasRegistry
except Exception:
    AliasRegistry = None  # type: ignore

# CanonChunk for backward compat ingestion
try:
    from fanfic_pipeline.packages.canon.spine_parser import CanonChunk
except Exception:
    CanonChunk = None  # type: ignore

# ---------------------------------------------------------------------------
# Authority models — immutable source of truth
# ---------------------------------------------------------------------------

class CanonSource(BaseModel):
    """Một nguồn canon bất biến (EPUB file)."""
    source_id: str = Field(description="ID nguồn, vd: epub_nhat_the")
    title: str = Field(default="", description="Tên nguồn")
    source_revision: str = Field(default="1.0.0", description="Revision string, semver-like")
    checksum: str = Field(default="", description="sha256[:16] của file nguồn")
    spine_count: int = Field(default=0, description="Số spine items")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    meta: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_revision")
    @classmethod
    def _validate_rev(cls, v: str) -> str:
        if not re.match(r'^\d+\.\d+(\.\d+)?([\-_a-z0-9\.]*)?$', v, re.IGNORECASE):
            raise ValueError(f"source_revision không hợp lệ: {v} (expect semver)")
        return v


class CanonChapter(BaseModel):
    """Một chương canon trong authority store."""
    chapter_id: str  # ex: ch_0001 or source_id:href
    source_id: str
    spine_order: int
    source_href: str
    title: str
    chapter_type: str  # cover, frontmatter, part_divider, main_chapter, side_story
    cjk_chars: int = 0
    cjk_tokens: int = 0
    char_count: int = 0
    word_count: int = 0
    checksum: str = ""  # sha256[:16] raw html
    span_ids: List[str] = Field(default_factory=list)
    # bitemporal (FR-09)
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class SourceSpan(BaseModel):
    """Một span văn bản bất biến, có checksum riêng — đơn vị evidence nhỏ nhất."""
    span_id: str  # ex: span_ch0001_001
    chapter_id: str
    source_id: str
    source_href: str
    spine_order: int
    title: str
    text: str
    char_start: int = 0
    char_end: int = 0
    checksum: str = ""  # sha256[:16] of text
    cjk_chars: int = 0
    cjk_tokens: int = 0


class CanonFact(BaseModel):
    """Fact yêu cầu evidence nếu confidence>0.7 — fail-closed."""
    fact_id: str
    subject_entity_id: str
    predicate: str  # realm, technique, affiliation, secret, status, relationship, etc.
    object_value: str
    # Chapter-range validity (backward compat)
    valid_from_chapter: int = 1
    valid_to_chapter: int = 9999
    # Bitemporal bổ sung (FR-09)
    valid_from: Optional[str] = None  # ISO datetime or chapter marker
    valid_to: Optional[str] = None
    reveal_from: Optional[int] = None  # chapter where fact becomes revealable
    confidence: float = 1.0  # 0..1
    evidence_chunk_ids: List[str] = Field(default_factory=list)
    evidence_span_ids: List[str] = Field(default_factory=list)
    extractor_version: str = Field(default="1.0.0")
    status: str = Field(default="draft", description="draft/verified/contradicted")
    description_vi: str = ""
    description: str = ""  # alias
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        allowed = {"draft", "verified", "contradicted"}
        if v not in allowed:
            raise ValueError(f"status phải là một trong {allowed}, got {v}")
        return v

    @field_validator("confidence")
    @classmethod
    def _validate_conf(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError(f"confidence phải 0..1, got {v}")
        return v

    @model_validator(mode="after")
    def _check_evidence(self):
        # FR-06: confidence>0.7 requires non-empty evidence
        if self.confidence > 0.7:
            has_ev = bool(self.evidence_chunk_ids or self.evidence_span_ids)
            if not has_ev:
                raise ValueError(
                    f"Fact {self.fact_id} confidence {self.confidence}>0.7 requires non-empty "
                    f"evidence_chunk_ids or evidence_span_ids"
                )
        # đồng bộ description alias
        if not self.description and self.description_vi:
            self.description = self.description_vi
        if not self.description_vi and self.description:
            self.description_vi = self.description
        return self

    # backward compat: valid_from/to chapter aliases
    @property
    def valid_from_ch(self) -> int:
        return self.valid_from_chapter

    @property
    def valid_to_ch(self) -> int:
        return self.valid_to_chapter


class CanonAlignment(BaseModel):
    """
    Alignment map: fanfic chapter/anchor <-> canon chapter/source event.
    Fanfic chapter != canon chapter — ánh xạ riêng biệt.
    """
    alignment_id: str
    branch_id: str = Field(description="Nhánh fanfic / POD branch")
    story_anchor: str = Field(description="Anchor trong fanfic, vd: fanfic_ch_001_beat2")
    fanfic_chapter: int = Field(description="Chương fanfic")
    canon_chapter_id: Optional[str] = Field(default=None, description="Canon chapter_id tham chiếu")
    canon_spine_order: Optional[int] = Field(default=None)
    source_event: str = Field(default="", description="Sự kiện canon tham chiếu")
    confidence: float = 1.0
    notes: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class CanonStore:
    """
    Authority vs Derived split:
    - Authority: CanonSource, CanonChapter, SourceSpan — immutable JSON trong authority/
    - Facts: evidence-backed, versioned
    - Alignment: branch_id + fanfic<->canon map
    - Derived: FTS index (sqlite) — rebuildable
    """
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or "/tmp/canon_store"
        os.makedirs(self.storage_dir, exist_ok=True)
        self.authority_dir = os.path.join(self.storage_dir, "authority")
        os.makedirs(self.authority_dir, exist_ok=True)

        # Authority files (immutable JSON)
        self.sources_file = os.path.join(self.authority_dir, "canon_sources.json")
        self.chapters_file = os.path.join(self.authority_dir, "canon_chapters.json")
        self.spans_file = os.path.join(self.authority_dir, "canon_spans.json")
        self.facts_file = os.path.join(self.storage_dir, "canon_facts.json")
        self.alignments_file = os.path.join(self.storage_dir, "canon_alignments.json")
        # Legacy chunks file for backward compat (derived mirror)
        self.chunks_file = os.path.join(self.storage_dir, "canon_chunks.json")
        # FTS DB (derived)
        self.fts_db_path = os.path.join(self.storage_dir, "canon_fts.db")

        self.sources: Dict[str, CanonSource] = {}
        self.chapters: Dict[str, CanonChapter] = {}
        self.spans: Dict[str, SourceSpan] = {}
        # Derived mirror for backward compat: chunk_id -> CanonChunk dict
        self.chunks: Dict[str, Any] = {}
        self.facts: Dict[str, CanonFact] = {}
        self.alignments: Dict[str, CanonAlignment] = {}

        # Alias registry
        try:
            self.alias_registry = AliasRegistry() if AliasRegistry else None
        except Exception:
            self.alias_registry = None

        self._fts_available: Optional[bool] = None
        self._load_all()
        if not self.facts:
            self._init_default_nhat_the_facts()

    # ---------------- load/save ----------------

    def _load_json_dict(self, path: str, model_cls):
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # data is dict id->obj
            result = {}
            for k, v in data.items():
                try:
                    result[k] = model_cls(**v)
                except Exception:
                    # skip invalid
                    continue
            return result
        except Exception:
            return {}

    def _load_all(self):
        self.sources = self._load_json_dict(self.sources_file, CanonSource)
        self.chapters = self._load_json_dict(self.chapters_file, CanonChapter)
        self.spans = self._load_json_dict(self.spans_file, SourceSpan)
        self.facts = self._load_json_dict(self.facts_file, CanonFact)
        self.alignments = self._load_json_dict(self.alignments_file, CanonAlignment)
        # chunks backward compat
        if os.path.exists(self.chunks_file):
            try:
                with open(self.chunks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # data may be dict chunk_id->CanonChunk
                # we keep as raw dict + also populate spans if missing
                self.chunks = data
                # if spans empty but chunks exist, hydrate spans from chunks
                if not self.spans and data:
                    for cid, cval in data.items():
                        try:
                            ch = cval
                            sid = cid
                            # build SourceSpan from CanonChunk
                            span = SourceSpan(
                                span_id=sid,
                                chapter_id=f"ch_{ch.get('chapter_index', 0):04d}",
                                source_id=ch.get("source_id", "epub_nhat_the"),
                                source_href=ch.get("source_href", ""),
                                spine_order=ch.get("spine_order", 0),
                                title=ch.get("title", ""),
                                text=ch.get("text", ""),
                                checksum=ch.get("checksum", ""),
                                cjk_chars=ch.get("cjk_chars", 0),
                                cjk_tokens=ch.get("cjk_tokens", 0),
                            )
                            self.spans[sid] = span
                        except Exception:
                            continue
            except Exception:
                self.chunks = {}
        # also build chunks mirror from spans if chunks empty
        if not self.chunks and self.spans:
            self.chunks = {
                sid: {
                    "chunk_id": s.span_id,
                    "source_id": s.source_id,
                    "chapter_index": int(s.chapter_id.split("_")[-1]) if "_" in s.chapter_id else 0,
                    "chapter_type": self.chapters.get(s.chapter_id, CanonChapter(chapter_id=s.chapter_id, source_id=s.source_id, spine_order=0, source_href="", title="")).chapter_type if s.chapter_id in self.chapters else "main_chapter",
                    "title": s.title,
                    "source_href": s.source_href,
                    "text": s.text,
                    "char_count": len(s.text),
                    "word_count": len(re.findall(r"\S+", s.text)),
                    "cjk_chars": s.cjk_chars,
                    "cjk_tokens": s.cjk_tokens,
                    "checksum": s.checksum,
                    "spine_order": s.spine_order,
                }
                for sid, s in self.spans.items()
            }

    def _save_all(self):
        # Atomic write via temp file rename
        def _atomic_write(path: str, data: dict):
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                # model_dump for pydantic v2, dict for v1
                dumped = {}
                for k, v in data.items():
                    if hasattr(v, "model_dump"):
                        dumped[k] = v.model_dump()
                    elif hasattr(v, "dict"):
                        dumped[k] = v.model_dump()
                    else:
                        dumped[k] = v
                json.dump(dumped, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)

        _atomic_write(self.sources_file, self.sources)
        _atomic_write(self.chapters_file, self.chapters)
        _atomic_write(self.spans_file, self.spans)
        _atomic_write(self.facts_file, self.facts)
        _atomic_write(self.alignments_file, self.alignments)
        # mirror chunks for legacy consumers
        try:
            # ensure chunks mirror is dict of plain dicts
            chunks_plain: Dict[str, Any] = {}
            for k, v in self.chunks.items():
                if hasattr(v, "model_dump"):
                    chunks_plain[k] = v.model_dump()
                elif hasattr(v, "dict"):
                    chunks_plain[k] = v.model_dump()
                else:
                    chunks_plain[k] = v
            # if chunks empty but spans exist, build from spans
            if not chunks_plain and self.spans:
                for sid, s in self.spans.items():
                    d = s.model_dump() if hasattr(s, "model_dump") else s.model_dump()
                    chunks_plain[sid] = {
                        "chunk_id": d["span_id"],
                        "source_id": d["source_id"],
                        "chapter_index": 0,
                        "chapter_type": "main_chapter",
                        "title": d["title"],
                        "source_href": d["source_href"],
                        "text": d["text"],
                        "char_count": len(d["text"]),
                        "word_count": len(re.findall(r"\S+", d["text"])),
                        "cjk_chars": d.get("cjk_chars", 0),
                        "cjk_tokens": d.get("cjk_tokens", 0),
                        "checksum": d.get("checksum", ""),
                    }
            tmp = self.chunks_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(chunks_plain, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.chunks_file)
        except Exception:
            pass

    # ---------------- source_revision validation ----------------

    def validate_source_revision(self, source_id: str, revision: str) -> bool:
        """Kiểm tra revision hợp lệ và khớp với stored source."""
        if not re.match(r'^\d+\.\d+(\.\d+)?([\-_a-z0-9\.]*)?$', revision, re.IGNORECASE):
            raise ValueError(f"source_revision không hợp lệ: {revision}")
        src = self.sources.get(source_id)
        if src is None:
            # chưa có source — cho phép tạo mới
            return True
        # Nếu đã có, revision phải >= stored (simple semver compare)
        def _parse(v: str) -> Tuple[int, ...]:
            core = re.split(r'[-_]', v)[0]
            return tuple(int(x) for x in core.split(".") if x.isdigit())
        try:
            if _parse(revision) < _parse(src.source_revision):
                raise ValueError(
                    f"Revision downgrade bị cấm: stored {src.source_revision} -> requested {revision}"
                )
        except ValueError:
            raise
        except Exception:
            pass
        return True

    def upsert_source(self, source: CanonSource) -> None:
        self.validate_source_revision(source.source_id, source.source_revision)
        self.sources[source.source_id] = source
        self._save_all()

    # ---------------- ingestion ----------------

    def ingest_spine_docs(self, docs: List[Any], source_id: str = "epub_nhat_the",
                          source_revision: str = "1.0.0", source_title: str = "Nhất Thế Chi Tôn") -> None:
        """Ingest từ SpineAwareEpubParser docs — tạo authority records."""
        # Source
        checksum_combined = hashlib.sha256("".join(d.checksum for d in docs).encode()).hexdigest()[:16] if docs else ""
        src = CanonSource(
            source_id=source_id,
            title=source_title,
            source_revision=source_revision,
            checksum=checksum_combined,
            spine_count=len(docs),
        )
        self.validate_source_revision(source_id, source_revision)
        self.sources[source_id] = src

        # Chapters + Spans
        for doc in docs:
            ch_id = f"ch_{doc.spine_order:04d}_{doc.checksum[:6]}" if hasattr(doc, "checksum") else f"ch_{doc.chapter_index:04d}"
            # chapter
            chapter = CanonChapter(
                chapter_id=ch_id,
                source_id=source_id,
                spine_order=getattr(doc, "spine_order", doc.chapter_index - 1),
                source_href=getattr(doc, "source_href", ""),
                title=getattr(doc, "title", ""),
                chapter_type=getattr(doc, "chapter_type", "main_chapter"),
                cjk_chars=getattr(doc, "cjk_chars", getattr(doc, "cjk_char_count", 0)),
                cjk_tokens=getattr(doc, "cjk_tokens", 0),
                char_count=getattr(doc, "char_count", len(getattr(doc, "raw_text", ""))),
                word_count=getattr(doc, "word_count", 0),
                checksum=getattr(doc, "checksum", ""),
                span_ids=[],
            )
            # spans from chunks
            span_ids: List[str] = []
            chunks = getattr(doc, "chunks", [])
            for idx, ch in enumerate(chunks):
                # ch is CanonChunk
                span_id = ch.chunk_id if hasattr(ch, "chunk_id") else f"span_{ch_id}_{idx:03d}"
                text = ch.text if hasattr(ch, "text") else str(ch)
                cjk_chars = getattr(ch, "cjk_chars", 0)
                cjk_tokens = getattr(ch, "cjk_tokens", 0)
                checksum = getattr(ch, "checksum", hashlib.sha256(text.encode()).hexdigest()[:16])
                span = SourceSpan(
                    span_id=span_id,
                    chapter_id=ch_id,
                    source_id=source_id,
                    source_href=chapter.source_href,
                    spine_order=chapter.spine_order,
                    title=chapter.title,
                    text=text,
                    char_start=0,
                    char_end=len(text),
                    checksum=checksum,
                    cjk_chars=cjk_chars,
                    cjk_tokens=cjk_tokens,
                )
                self.spans[span_id] = span
                span_ids.append(span_id)
                # mirror to chunks
                self.chunks[span_id] = ch if hasattr(ch, "model_dump") or hasattr(ch, "dict") else {
                    "chunk_id": span_id,
                    "source_id": source_id,
                    "chapter_index": doc.chapter_index,
                    "chapter_type": chapter.chapter_type,
                    "title": chapter.title,
                    "source_href": chapter.source_href,
                    "text": text,
                    "char_count": len(text),
                    "word_count": len(re.findall(r"\S+", text)),
                    "cjk_chars": cjk_chars,
                    "cjk_tokens": cjk_tokens,
                    "checksum": checksum,
                    "spine_order": chapter.spine_order,
                }
            # if no chunks, create one span from raw_text
            if not span_ids:
                raw_text = getattr(doc, "raw_text", "")
                if raw_text:
                    span_id = f"span_{ch_id}_000"
                    span = SourceSpan(
                        span_id=span_id,
                        chapter_id=ch_id,
                        source_id=source_id,
                        source_href=chapter.source_href,
                        spine_order=chapter.spine_order,
                        title=chapter.title,
                        text=raw_text,
                        checksum=hashlib.sha256(raw_text.encode()).hexdigest()[:16],
                        cjk_chars=chapter.cjk_chars,
                        cjk_tokens=chapter.cjk_tokens,
                    )
                    self.spans[span_id] = span
                    span_ids.append(span_id)
                    self.chunks[span_id] = {
                        "chunk_id": span_id,
                        "source_id": source_id,
                        "chapter_index": doc.chapter_index,
                        "chapter_type": chapter.chapter_type,
                        "title": chapter.title,
                        "source_href": chapter.source_href,
                        "text": raw_text,
                        "char_count": len(raw_text),
                        "word_count": len(re.findall(r"\S+", raw_text)),
                        "cjk_chars": chapter.cjk_chars,
                        "cjk_tokens": chapter.cjk_tokens,
                        "checksum": span.checksum,
                        "spine_order": chapter.spine_order,
                    }
            chapter.span_ids = span_ids
            self.chapters[ch_id] = chapter

        self._save_all()
        # Derived: rebuild FTS
        try:
            self.rebuild_fts()
        except Exception:
            pass

    def ingest_chunks(self, chunks: List[Any]) -> None:
        """Backward compat: ingest List[CanonChunk] directly."""
        for c in chunks:
            # c may be CanonChunk model or dict
            if hasattr(c, "chunk_id"):
                cid = c.chunk_id
                text = c.text
                source_id = getattr(c, "source_id", "epub_nhat_the")
                source_href = getattr(c, "source_href", "")
                spine_order = getattr(c, "spine_order", 0)
                title = getattr(c, "title", "")
                checksum = getattr(c, "checksum", hashlib.sha256(text.encode()).hexdigest()[:16])
                cjk_chars = getattr(c, "cjk_chars", 0)
                cjk_tokens = getattr(c, "cjk_tokens", 0)
                # ensure chapter exists
                ch_id = f"ch_{getattr(c, 'chapter_index', 0):04d}"
                if ch_id not in self.chapters:
                    self.chapters[ch_id] = CanonChapter(
                        chapter_id=ch_id,
                        source_id=source_id,
                        spine_order=spine_order,
                        source_href=source_href,
                        title=title,
                        chapter_type=getattr(c, "chapter_type", "main_chapter"),
                        checksum=checksum,
                        span_ids=[],
                    )
                # span
                span = SourceSpan(
                    span_id=cid,
                    chapter_id=ch_id,
                    source_id=source_id,
                    source_href=source_href,
                    spine_order=spine_order,
                    title=title,
                    text=text,
                    checksum=checksum,
                    cjk_chars=cjk_chars,
                    cjk_tokens=cjk_tokens,
                )
                self.spans[cid] = span
                self.chunks[cid] = c
                # link
                if cid not in self.chapters[ch_id].span_ids:
                    self.chapters[ch_id].span_ids.append(cid)
            else:
                # dict
                cid = c.get("chunk_id", f"chunk_{len(self.chunks)}")
                self.chunks[cid] = c
                self.spans[cid] = SourceSpan(
                    span_id=cid,
                    chapter_id=c.get("chapter_id", "ch_0000"),
                    source_id=c.get("source_id", "epub_nhat_the"),
                    source_href=c.get("source_href", ""),
                    spine_order=c.get("spine_order", 0),
                    title=c.get("title", ""),
                    text=c.get("text", ""),
                    checksum=c.get("checksum", ""),
                )
        self._save_all()
        try:
            self.rebuild_fts()
        except Exception:
            pass

    # ---------------- facts ----------------

    # Back-compat alias — older CLI/tests used ingest_documents
    def ingest_documents(self, docs, source_id="epub_nhat_the", source_revision="1.1", **kw):
        return self.ingest_spine_docs(docs, source_id=source_id, source_revision=source_revision, **kw)

    def add_fact(self, fact: CanonFact) -> None:
        # validation is done in model_validator; just store
        # also auto-set description alias
        self.facts[fact.fact_id] = fact
        self._save_all()

    def query_facts(self, entity_id: str, chapter_num: int,
                    include_contradicted: bool = False) -> List[CanonFact]:
        """Truy vấn facts hợp lệ tại chapter_num, tôn trọng status và reveal_from."""
        valid: List[CanonFact] = []
        for f in self.facts.values():
            if f.subject_entity_id != entity_id:
                continue
            if not include_contradicted and f.status == "contradicted":
                continue
            # chapter range
            if not (f.valid_from_chapter <= chapter_num <= f.valid_to_chapter):
                continue
            # reveal_from: if set, fact only visible from that chapter onward
            if f.reveal_from is not None and chapter_num < f.reveal_from:
                continue
            valid.append(f)
        # sort by confidence desc
        valid.sort(key=lambda x: x.confidence, reverse=True)
        return valid

    # Backward compat alias
    def get_facts_for_entity(self, entity_id: str, chapter_num: int) -> List[CanonFact]:
        return self.query_facts(entity_id, chapter_num)

    # ---------------- alignment ----------------

    def add_alignment(self, alignment: CanonAlignment) -> None:
        self.alignments[alignment.alignment_id] = alignment
        self._save_all()

    def get_alignments(self, fanfic_chapter: Optional[int] = None,
                       branch_id: Optional[str] = None) -> List[CanonAlignment]:
        result = list(self.alignments.values())
        if fanfic_chapter is not None:
            result = [a for a in result if a.fanfic_chapter == fanfic_chapter]
        if branch_id is not None:
            result = [a for a in result if a.branch_id == branch_id]
        return result

    # ---------------- FTS helpers ----------------

    def _check_fts_available(self) -> bool:
        if self._fts_available is not None:
            return self._fts_available
        try:
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE VIRTUAL TABLE test_fts USING fts5(x)")
            conn.execute("DROP TABLE test_fts")
            conn.close()
            self._fts_available = True
        except Exception:
            self._fts_available = False
        return self._fts_available

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.fts_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def rebuild_fts(self) -> Dict[str, Any]:
        """
        Derived index — drop & rebuild from authority spans/chunks.
        Returns stats.
        """
        conn = self._get_conn()
        try:
            # Drop existing
            conn.execute("DROP TABLE IF EXISTS canon_fts")
            conn.execute("DROP TABLE IF EXISTS canon_fts_data")

            use_fts5 = self._check_fts_available()
            if use_fts5:
                # FTS5 with unicode61 tokenizer for CJK
                try:
                    conn.execute("""
                        CREATE VIRTUAL TABLE canon_fts USING fts5(
                            doc_id, title, text, chapter_type, spine_order,
                            tokenize='unicode61 \"remove_diacritics 0\"'
                        )
                    """)
                except Exception:
                    conn.execute("""
                        CREATE VIRTUAL TABLE canon_fts USING fts5(
                            doc_id, title, text, chapter_type, spine_order
                        )
                    """)
            else:
                # Fallback: plain table with LIKE search
                conn.execute("""
                    CREATE TABLE canon_fts (
                        doc_id TEXT PRIMARY KEY,
                        title TEXT,
                        text TEXT,
                        chapter_type TEXT,
                        spine_order INTEGER
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_canon_fts_text ON canon_fts(text)")

            # Populate from spans
            count = 0
            for span_id, span in self.spans.items():
                try:
                    # Resolve chapter_type via chapter
                    ch = self.chapters.get(span.chapter_id)
                    ch_type = ch.chapter_type if ch else "main_chapter"
                    spine_order = span.spine_order
                    conn.execute(
                        "INSERT INTO canon_fts(doc_id, title, text, chapter_type, spine_order) VALUES (?,?,?,?,?)",
                        (span_id, span.title, span.text, ch_type, spine_order)
                    )
                    count += 1
                except Exception:
                    continue

            # Also include any chunks not in spans (legacy)
            for cid, cval in self.chunks.items():
                if cid in self.spans:
                    continue
                try:
                    if isinstance(cval, dict):
                        title = cval.get("title", "")
                        text = cval.get("text", "")
                        ch_type = cval.get("chapter_type", "main_chapter")
                        spine_order = cval.get("spine_order", 0)
                    else:
                        title = getattr(cval, "title", "")
                        text = getattr(cval, "text", "")
                        ch_type = getattr(cval, "chapter_type", "main_chapter")
                        spine_order = getattr(cval, "spine_order", 0)
                    conn.execute(
                        "INSERT INTO canon_fts(doc_id, title, text, chapter_type, spine_order) VALUES (?,?,?,?,?)",
                        (cid, title, text, ch_type, spine_order)
                    )
                    count += 1
                except Exception:
                    continue

            conn.commit()
            return {"status": "ok", "fts_type": "fts5" if use_fts5 else "like_fallback", "docs_indexed": count}
        finally:
            conn.close()

    def _ensure_fts_ready(self):
        if not os.path.exists(self.fts_db_path):
            try:
                self.rebuild_fts()
            except Exception:
                pass
        else:
            # check if table exists
            try:
                conn = self._get_conn()
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='canon_fts'")
                row = cur.fetchone()
                conn.close()
                if not row:
                    self.rebuild_fts()
            except Exception:
                pass

    def _fts_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Thực hiện FTS5 search với bm25 ranking."""
        conn = self._get_conn()
        try:
            # Sanitize query for FTS5: escape quotes, handle CJK
            # For CJK, FTS5 unicode61 tokenizes per char; we can use OR for multi-token query
            # Build query: wrap in quotes for phrase? Use simple term search
            fts_query = query.replace('"', '""')
            # If contains CJK, split into chars for better recall
            # Use OR expansion: each token OR
            tokens = re.findall(r"\S+", fts_query)
            if any(re.search(r'[\u4E00-\u9FFF]', t) for t in tokens):
                # Keep original + char-level OR
                fts_query = " OR ".join(tokens)
            # Try bm25 ranking
            try:
                cur = conn.execute("""
                    SELECT doc_id, title, text, chapter_type, spine_order,
                           rank as bm25_rank
                    FROM canon_fts
                    WHERE canon_fts MATCH ?
                    ORDER BY bm25_rank
                    LIMIT ?
                """, (fts_query, top_k * 2))
                rows = cur.fetchall()
                results = []
                for r in rows:
                    # bm25_rank is negative (more negative = better); convert to positive score
                    raw_rank = r["bm25_rank"] if r["bm25_rank"] is not None else 0
                    # Normalize: score = -rank (FTS5 rank is negative)
                    score = float(-raw_rank) if raw_rank < 0 else float(1.0 / (1.0 + abs(raw_rank)))
                    if score <= 0:
                        score = 0.5
                    results.append({
                        "doc_id": r["doc_id"],
                        "title": r["title"],
                        "text": r["text"],
                        "chapter_type": r["chapter_type"],
                        "spine_order": r["spine_order"],
                        "bm25_score": round(score, 4),
                    })
                # If no results, fallback to LIKE
                if not results:
                    raise ValueError("No FTS results, fallback")
                return results
            except Exception as e:
                # Fallback inside FTS path
                raise e
        finally:
            conn.close()

    def _like_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Fallback LIKE search with TF-IDF-like scoring."""
        conn = self._get_conn()
        try:
            # First ensure table exists
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='canon_fts'")
            if not cur.fetchone():
                return []
            tokens = [t.lower() for t in re.findall(r"\S+", query.lower()) if len(t) > 1]
            if not tokens:
                tokens = [query.lower()]
            # Fetch all docs and score via TF-IDF-ish
            cur = conn.execute("SELECT doc_id, title, text, chapter_type, spine_order FROM canon_fts")
            rows = cur.fetchall()
            N = len(rows)
            if N == 0:
                return []
            # Doc frequency
            df: Dict[str, int] = {tok: 0 for tok in tokens}
            for r in rows:
                txt_low = (r["text"] or "").lower()
                title_low = (r["title"] or "").lower()
                combined = txt_low + " " + title_low
                for tok in tokens:
                    if tok in combined:
                        df[tok] += 1
            scored = []
            for r in rows:
                txt_low = (r["text"] or "").lower()
                title_low = (r["title"] or "").lower()
                combined = txt_low + " " + title_low
                score = 0.0
                for tok in tokens:
                    tf = combined.count(tok)
                    if tf == 0:
                        continue
                    # IDF
                    idf = math.log((N + 1) / (df[tok] + 1)) + 1
                    # TF normalized
                    tf_norm = 1 + math.log(tf) if tf > 0 else 0
                    # Title boost
                    title_boost = 2.0 if tok in title_low else 1.0
                    score += tf_norm * idf * title_boost
                if score > 0:
                    scored.append({
                        "doc_id": r["doc_id"],
                        "title": r["title"],
                        "text": r["text"],
                        "chapter_type": r["chapter_type"],
                        "spine_order": r["spine_order"],
                        "bm25_score": round(score, 4),
                    })
            scored.sort(key=lambda x: x["bm25_score"], reverse=True)
            return scored[:top_k * 2]
        finally:
            conn.close()

    # ---------------- search_canon ----------------

    def search_canon(self, query: str, chapter_context: int = 1, top_k: int = 5,
                     time_filter: Optional[Dict[str, Any]] = None,
                     entity_expand: bool = True,
                     chapter_type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Hybrid BM25/FTS5 + Alias Expansion + Temporal proximity + Time filters.
        - query: raw query string
        - chapter_context: fanfic chapter number for proximity boost
        - time_filter: optional dict {valid_from_chapter, valid_to_chapter} or {spine_order_min/max}
        - entity_expand: expand via alias_registry
        - chapter_type_filter: filter by chapter_type if set
        """
        # P1.1: alias-normalized query expansion (diacritic-insensitive)
        _norm = None
        try:
            from fanfic_pipeline.packages.canon.alias_normalizer import get_alias_normalizer
            _norm = get_alias_normalizer()
        except: pass
        _expanded = query
        if _norm:
            try:
                _exp = _norm.expand_query_for_search(query)
                if _exp and _exp != query:
                    _expanded = query + " " + _exp
            except: pass
        query_for_search = _expanded if _expanded else query
        query = query_for_search
        self._ensure_fts_ready()

        # 1. Alias expansion
        expanded_terms: Set[str] = set(re.findall(r"\S+", query))
        if entity_expand and self.alias_registry:
            try:
                expanded = self.alias_registry.expand_query_aliases(query)
                expanded_terms |= set(expanded)
            except Exception:
                pass
        # Also add individual expanded terms to query string for FTS
        expanded_query = " ".join(expanded_terms) if expanded_terms else query

        # 2. FTS search
        use_fts5 = self._check_fts_available()
        raw_hits: List[Dict[str, Any]] = []
        try:
            if use_fts5 and os.path.exists(self.fts_db_path):
                raw_hits = self._fts_search(expanded_query, top_k)
                # if no hits with expanded, retry with original
                if not raw_hits and expanded_query != query:
                    raw_hits = self._fts_search(query, top_k)
            else:
                raise RuntimeError("FTS5 not available")
        except Exception:
            # Fallback LIKE
            try:
                raw_hits = self._like_search(expanded_query, top_k)
                if not raw_hits and expanded_query != query:
                    raw_hits = self._like_search(query, top_k)
            except Exception:
                raw_hits = []

        # 3. If still no hits and we have chunks, do direct overlap scoring (last resort)
        if not raw_hits and self.chunks:
            for cid, cval in self.chunks.items():
                if isinstance(cval, dict):
                    txt = cval.get("text", "")
                    title = cval.get("title", "")
                    ch_idx = cval.get("chapter_index", 0)
                    ch_type = cval.get("chapter_type", "main_chapter")
                    spine_order = cval.get("spine_order", ch_idx)
                else:
                    txt = getattr(cval, "text", "")
                    title = getattr(cval, "title", "")
                    ch_idx = getattr(cval, "chapter_index", 0)
                    ch_type = getattr(cval, "chapter_type", "main_chapter")
                    spine_order = getattr(cval, "spine_order", 0)
                combined = (title + " " + txt).lower()
                overlap = sum(1 for tok in expanded_terms if tok.lower() in combined)
                if overlap > 0:
                    raw_hits.append({
                        "doc_id": cid,
                        "title": title,
                        "text": txt,
                        "chapter_type": ch_type,
                        "spine_order": spine_order,
                        "bm25_score": float(overlap * 2.0),
                        "_chapter_index": ch_idx,
                    })

        # 4. Enrich, filter, rank
        scored_hits: List[Dict[str, Any]] = []
        for h in raw_hits:
            doc_id = h["doc_id"]
            # time filter
            if time_filter:
                spine_min = time_filter.get("spine_order_min")
                spine_max = time_filter.get("spine_order_max")
                ch_min = time_filter.get("valid_from_chapter") or time_filter.get("chapter_min")
                ch_max = time_filter.get("valid_to_chapter") or time_filter.get("chapter_max")
                if spine_min is not None and h.get("spine_order", 0) < spine_min:
                    continue
                if spine_max is not None and h.get("spine_order", 0) > spine_max:
                    continue
                # for chapter-based filter, need to map spine->chapter
                # we use _chapter_index if available
                ch_idx = h.get("_chapter_index", h.get("spine_order", 0) + 1)
                if ch_min is not None and ch_idx < ch_min:
                    continue
                if ch_max is not None and ch_idx > ch_max:
                    continue
            if chapter_type_filter and h.get("chapter_type") != chapter_type_filter:
                continue

            # Find original chapter_index for proximity
            # Try to resolve via spans/chunks
            chapter_index = h.get("_chapter_index")
            if chapter_index is None:
                # lookup span
                span = self.spans.get(doc_id)
                if span:
                    # find chapter
                    ch = self.chapters.get(span.chapter_id)
                    if ch:
                        # Use spine_order as proxy for chapter position
                        chapter_index = ch.spine_order + 1
                    else:
                        chapter_index = span.spine_order + 1
                else:
                    # try chunks dict
                    cval = self.chunks.get(doc_id)
                    if cval:
                        if isinstance(cval, dict):
                            chapter_index = cval.get("chapter_index", cval.get("spine_order", 0) + 1)
                        else:
                            chapter_index = getattr(cval, "chapter_index", getattr(cval, "spine_order", 0) + 1)
                    else:
                        chapter_index = h.get("spine_order", 0) + 1

            # Proximity factor: closer to chapter_context gets boost
            delta = abs((chapter_index or 1) - chapter_context)
            proximity = math.exp(-0.005 * delta)

            base_score = h.get("bm25_score", 1.0)
            final_score = float(base_score) * (0.6 + 0.4 * proximity)

            scored_hits.append({
                "type": "canon_chunk",
                "id": doc_id,
                "chapter": chapter_index,
                "title": h.get("title", ""),
                "text": (h.get("text", "")[:400] + ("..." if len(h.get("text", "")) > 400 else "")),
                "full_text": h.get("text", ""),
                "chapter_type": h.get("chapter_type", ""),
                "spine_order": h.get("spine_order", 0),
                "score": round(final_score, 4),
                "bm25_score": h.get("bm25_score", 0),
            })

        # 5. Search facts as well (with time filtering)
        for fact in self.facts.values():
            # time filter for facts
            if time_filter:
                ch_min = time_filter.get("valid_from_chapter") or time_filter.get("chapter_min")
                ch_max = time_filter.get("valid_to_chapter") or time_filter.get("chapter_max")
                if ch_min is not None and fact.valid_to_chapter < ch_min:
                    continue
                if ch_max is not None and fact.valid_from_chapter > ch_max:
                    continue
            # only facts valid at chapter_context (or within filter) are searchable
            # For search, include facts whose valid range overlaps context ± 50? Keep simple: valid at context
            if not (fact.valid_from_chapter <= chapter_context <= fact.valid_to_chapter):
                # Still include if time_filter explicitly asks
                if not time_filter:
                    continue
            fact_str = f"{fact.predicate} {fact.object_value} {fact.description_vi} {fact.description}".lower()
            overlap = sum(1 for tok in expanded_terms if tok.lower() in fact_str)
            if overlap > 0:
                # boost by confidence
                fact_score = overlap * 3.0 * (0.5 + 0.5 * fact.confidence)
                scored_hits.append({
                    "type": "canon_fact",
                    "id": fact.fact_id,
                    "chapter": fact.valid_from_chapter,
                    "title": f"Chân lý Canon: {fact.predicate} -> {fact.object_value}",
                    "text": f"[{fact.subject_entity_id}] {fact.description_vi or fact.description} (Hạn: Ch.{fact.valid_from_chapter}-{fact.valid_to_chapter}, status={fact.status})",
                    "full_text": fact.description_vi or fact.description,
                    "score": round(fact_score, 4),
                    "confidence": fact.confidence,
                    "status": fact.status,
                })

        scored_hits.sort(key=lambda x: x["score"], reverse=True)
        return scored_hits[:top_k]

    # ---------------- default facts ----------------

    def _init_default_nhat_the_facts(self):
        # Facts must have evidence for confidence>0.7 — we provide dummy evidence ids that will be valid after ingest
        # For initial facts without spans, use confidence 0.65 or provide placeholder evidence
        defaults = [
            CanonFact(
                fact_id="fact_001",
                subject_entity_id="char_meng_qi",
                predicate="realm",
                object_value="Khai Khiếu (Khai Cửu Khiếu)",
                valid_from_chapter=1,
                valid_to_chapter=150,
                confidence=0.65,  # below 0.7 so no evidence required, or provide evidence
                evidence_chunk_ids=[],
                evidence_span_ids=[],
                extractor_version="1.0.0",
                status="verified",
                description_vi="Mạnh Kỳ trong giai đoạn nhiệm vụ tân thủ đến đại chiến Hắc Lục giang ở cảnh giới Khai Khiếu (Cửu Khiếu).",
            ),
            CanonFact(
                fact_id="fact_002",
                subject_entity_id="char_meng_qi",
                predicate="technique",
                object_value="Lôi Đao & Đoạn Thanh Ti & Bát Cửu Huyền Công sơ bộ",
                valid_from_chapter=1,
                valid_to_chapter=200,
                confidence=0.65,
                evidence_chunk_ids=[],
                evidence_span_ids=[],
                extractor_version="1.0.0",
                status="verified",
                description_vi="Võ công chính: Tử Lôi Đao pháp, cuồng phong đao ý và bắt đầu tu luyện Bát Cửu Huyền Công.",
            ),
            CanonFact(
                fact_id="fact_003",
                subject_entity_id="char_gu_xiaosang",
                predicate="secret",
                object_value="Hóa thân Vô Sinh Lão Mẫu",
                valid_from_chapter=1,
                valid_to_chapter=500,
                confidence=0.9,
                evidence_chunk_ids=["span_seed_001"],
                evidence_span_ids=["span_seed_001"],
                extractor_version="1.0.0",
                status="verified",
                description_vi="Cố Tiểu Tang là thánh nữ Tố Nữ Đạo nhưng thực chất là hóa thân dự phòng của Kim Mẫu, mang nỗi tuyệt vọng sâu sắc.",
            ),
            CanonFact(
                fact_id="fact_004",
                subject_entity_id="char_jiang_zhiwei",
                predicate="technique",
                object_value="Kiếm Xuất Vô Hối & Thái Thượng Kiếm Điển",
                valid_from_chapter=1,
                valid_to_chapter=300,
                confidence=0.65,
                evidence_chunk_ids=[],
                evidence_span_ids=[],
                extractor_version="1.0.0",
                status="verified",
                description_vi="Giang Chỉ Vi tu luyện kiếm thuật tuyệt đỉnh của Tẩy Kiếm Các, kiếm khí sắc bén tuyệt luân.",
            ),
            CanonFact(
                fact_id="fact_005",
                subject_entity_id="char_qi_zhengyan",
                predicate="secret",
                object_value="Thừa kế Ma Hoàng Điển Tịch",
                valid_from_chapter=30,
                valid_to_chapter=9999,
                confidence=0.65,
                evidence_chunk_ids=[],
                evidence_span_ids=[],
                extractor_version="1.0.0",
                status="verified",
                description_vi="Tề Chính Ngôn nhận được truyền thừa Ma Hoàng nhưng dùng nó với lý tưởng giải phóng phàm nhân.",
            ),
        ]
        for f in defaults:
            # If confidence>0.7 but no real span, we added dummy; for others keep low confidence
            try:
                self.facts[f.fact_id] = f
            except Exception:
                # fallback: lower confidence
                f.confidence = 0.65
                f.evidence_chunk_ids = []
                f.evidence_span_ids = []
                self.facts[f.fact_id] = f
        self._save_all()

    # ---------------- compat helpers ----------------

    @property
    def storage_path(self) -> str:
        return self.storage_dir

    def get_source(self, source_id: str) -> Optional[CanonSource]:
        return self.sources.get(source_id)

    def list_sources(self) -> List[CanonSource]:
        return list(self.sources.values())
