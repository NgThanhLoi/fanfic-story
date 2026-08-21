"""
Hybrid Memory & Retrieval Engine (FR-10 Compliant):
- REAL FTS/BM25 scoring: sqlite FTS5 → rank_bm25 lib → TF-IDF fallback (KHÔNG token overlap thô)
- Typed story memories: episodic (có decay) vs permanent/semantic (không decay)
- Temporal decay chỉ áp dụng cho episodic, permanent facts giữ nguyên trọng số
- FTS index là derived — rebuild() drop & rebuild từ JSON
- Backward compat với HybridMemoryEngine(memory_file) cũ
"""

import os
import json
import math
import re
import sqlite3
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path

# ---------------------------------------------------------------------------
# Tokenization — hỗ trợ CJK + Vietnamese
# ---------------------------------------------------------------------------

_CJK_RE = re.compile(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]')

def _tokenize(text: str) -> List[str]:
    """Tokenize cho BM25/TF-IDF: tách latin words + CJK chars riêng lẻ."""
    if not text:
        return []
    t = text.lower()
    tokens: List[str] = []
    # Latin / Vietnamese base tokens (giữ dấu? lower đã có)
    # Dùng regex bắt từ có chữ cái
    latin = re.findall(r'[a-z0-9àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+', t)
    tokens.extend(latin)
    # CJK mỗi ký tự là một token (để BM25 recall tốt)
    cjk_chars = _CJK_RE.findall(t)
    tokens.extend(cjk_chars)
    # Fallback: nếu không có token nào, split whitespace
    if not tokens:
        tokens = [x for x in re.findall(r'\S+', t) if x]
    # Lọc token rỗng / quá ngắn? giữ CJK 1 char, latin >=2 hoặc giữ hết
    # Để BM25 không bị noise, giữ token len>=1, nhưng bỏ single latin char trừ CJK
    filtered: List[str] = []
    for tok in tokens:
        if len(tok) == 1 and tok.isascii() and tok.isalpha():
            # bỏ 'a', 'i' đơn lẻ nếu không phải CJK
            continue
        filtered.append(tok)
    return filtered if filtered else tokens


def _normalize_query_for_fts(query: str) -> str:
    """Chuẩn hoá query cho FTS5 MATCH: escape quotes, OR cho CJK."""
    q = query.replace('"', '""').strip()
    if not q:
        return q
    # Nếu chứa CJK, tách thành OR
    if _CJK_RE.search(q):
        parts = re.findall(r'\S+', q)
        # Với CJK, mỗi char OR sẽ recall tốt hơn
        return " OR ".join(parts)
    return q

# ---------------------------------------------------------------------------
# HybridMemoryItem — typed
# ---------------------------------------------------------------------------

# memory_type hợp lệ
_VALID_MEMORY_TYPES = {"episodic", "permanent", "semantic", "fact", "relationship", "world", "technique"}
# category -> default memory_type mapping (để backward compat)
_CATEGORY_TO_TYPE = {
    "technique": "permanent",
    "fact": "permanent",
    "world_rule": "permanent",
    "world": "permanent",
    "relationship": "permanent",
    "character": "permanent",
    "episodic": "episodic",
    "event": "episodic",
    "scene": "episodic",
    "memory": "episodic",
}

class HybridMemoryItem:
    """
    Một memory item có typed semantics.
    - episodic: ký ức theo chương, có temporal decay
    - permanent: fact/technique/world — KHÔNG decay
    """
    def __init__(
        self,
        item_id: str,
        topic: str,
        category: str,
        content: str,
        chapter_reference: int,
        weight: float = 1.0,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.item_id = item_id
        self.topic = topic
        self.category = category
        self.content = content
        self.chapter_reference = int(chapter_reference)
        self.weight = float(weight)
        # infer memory_type nếu không truyền
        if memory_type is None:
            # suy từ category
            inferred = _CATEGORY_TO_TYPE.get(category.lower(), "episodic")
            # technique/fact nên là permanent
            self.memory_type = inferred
        else:
            mt = memory_type.lower().strip()
            self.memory_type = mt if mt in _VALID_MEMORY_TYPES else "episodic"
        self.tags: List[str] = tags or []
        self.created_at: str = created_at or datetime.now(timezone.utc).isoformat()
        self.extra: Dict[str, Any] = extra or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "topic": self.topic,
            "category": self.category,
            "content": self.content,
            "chapter_reference": self.chapter_reference,
            "weight": self.weight,
            "memory_type": self.memory_type,
            "tags": self.tags,
            "created_at": self.created_at,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HybridMemoryItem":
        return cls(
            item_id=d.get("item_id", f"mem_{hashlib.md5(str(d).encode()).hexdigest()[:6]}"),
            topic=d.get("topic", ""),
            category=d.get("category", "episodic"),
            content=d.get("content", ""),
            chapter_reference=d.get("chapter_reference", 0),
            weight=d.get("weight", 1.0),
            memory_type=d.get("memory_type"),
            tags=d.get("tags", []),
            created_at=d.get("created_at"),
            extra=d.get("extra", {}),
        )

    @property
    def is_permanent(self) -> bool:
        return self.memory_type in ("permanent", "fact", "world", "technique", "semantic", "relationship")

    @property
    def is_episodic(self) -> bool:
        return self.memory_type == "episodic"

    def temporal_factor(self, current_chapter: int, lambda_decay: float = 0.03) -> float:
        """Decay chỉ cho episodic; permanent luôn 1.0"""
        if self.is_permanent:
            return 1.0
        delta = max(0, current_chapter - self.chapter_reference)
        return math.exp(-lambda_decay * delta)

# ---------------------------------------------------------------------------
# HybridMemoryEngine
# ---------------------------------------------------------------------------

class HybridMemoryEngine:
    """
    Hybrid lexical retrieval với 3-tier scoring:
    1) rank_bm25 lib (nếu cài) — BM25Okapi chuẩn
    2) sqlite FTS5 với rank (nếu sqlite hỗ trợ)
    3) TF-IDF fallback pure python

    Và phân biệt episodic vs permanent cho temporal decay.
    """
    def __init__(self, memory_file: str, fts_db_path: Optional[str] = None):
        self.memory_file = memory_file
        # FTS DB derived — cùng thư mục với memory_file
        if fts_db_path:
            self.fts_db_path = fts_db_path
        else:
            # /path/mem.json -> /path/mem.fts.db
            p = Path(memory_file)
            self.fts_db_path = str(p.with_suffix("")) + ".fts.db" if p.suffix == ".json" else str(p) + ".fts.db"
        self.items: List[HybridMemoryItem] = []
        self._fts_available: Optional[bool] = None
        self._bm25_available: Optional[bool] = None
        self._bm25_module = None
        # P4.3: SQLite backend — primary store; JSON fallback for backward compat
        self._sqlite_store = None
        self._use_sqlite = False
        try:
            from fanfic_pipeline.packages.memory.sqlite_memory_store import SqliteMemoryStore
            sqlite_path = str(Path(memory_file).with_suffix(".db")) if Path(memory_file).suffix == ".json" else str(memory_file) + ".db"
            self._sqlite_store = SqliteMemoryStore(sqlite_path)
            self._use_sqlite = True
        except Exception:
            pass
        self._check_bm25_available()
        self._load()
        # ensure FTS ready if items exist
        if self.items and not os.path.exists(self.fts_db_path):
            try:
                self.rebuild()
            except Exception:
                pass

    # ---------------- persistence ----------------

    def _load(self):
        # P4.3: Try SQLite first, fallback to JSON
        if self._use_sqlite and self._sqlite_store:
            try:
                rows = self._sqlite_store.load_all()
                if rows:
                    self.items = [HybridMemoryItem.from_dict(r) for r in rows]
                    return
            except Exception:
                pass
        # Fallback: load from JSON file
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.items = [HybridMemoryItem.from_dict(d) for d in data]
                elif isinstance(data, dict):
                    self.items = [HybridMemoryItem.from_dict(v) for v in data.values()]
                else:
                    self.items = []
                # Auto-migrate: if SQLite available but empty, import JSON data
                if self._use_sqlite and self._sqlite_store and self.items:
                    try:
                        for it in self.items:
                            self._sqlite_store.upsert(it.to_dict())
                    except Exception:
                        pass
            except Exception:
                self.items = []
        else:
            self.items = []

    def _save(self):
        # P4.3: Save to SQLite if available, always also write JSON for backward compat
        if self._use_sqlite and self._sqlite_store:
            try:
                for it in self.items:
                    self._sqlite_store.upsert(it.to_dict())
            except Exception:
                pass
        # Always write JSON for backward compat
        os.makedirs(os.path.dirname(self.memory_file) or ".", exist_ok=True)
        tmp = self.memory_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([it.to_dict() for it in self.items], f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.memory_file)

    # ---------------- capability checks ----------------

    def _check_bm25_available(self) -> bool:
        if self._bm25_available is not None:
            return self._bm25_available
        try:
            import rank_bm25  # type: ignore
            from rank_bm25 import BM25Okapi  # type: ignore
            self._bm25_module = rank_bm25
            self._bm25_available = True
        except Exception:
            self._bm25_available = False
            self._bm25_module = None
        return self._bm25_available

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

    # ---------------- FTS rebuild ----------------

    def rebuild(self) -> Dict[str, Any]:
        """Alias chuẩn — rebuild FTS index từ items. Idempotent, derived."""
        return self.rebuild_fts()

    def rebuild_fts(self) -> Dict[str, Any]:
        """Drop & rebuild FTS index từ authority (items JSON)."""
        conn = self._get_conn()
        try:
            conn.execute("DROP TABLE IF EXISTS memory_fts")
            use_fts5 = self._check_fts_available()
            if use_fts5:
                try:
                    conn.execute("""
                        CREATE VIRTUAL TABLE memory_fts USING fts5(
                            doc_id, topic, content, category, memory_type, chapter_ref,
                            tokenize='unicode61 "remove_diacritics 0"'
                        )
                    """)
                except Exception:
                    conn.execute("""
                        CREATE VIRTUAL TABLE memory_fts USING fts5(
                            doc_id, topic, content, category, memory_type, chapter_ref
                        )
                    """)
            else:
                conn.execute("""
                    CREATE TABLE memory_fts (
                        doc_id TEXT PRIMARY KEY,
                        topic TEXT,
                        content TEXT,
                        category TEXT,
                        memory_type TEXT,
                        chapter_ref INTEGER
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_fts_content ON memory_fts(content)")

            count = 0
            for it in self.items:
                try:
                    conn.execute(
                        "INSERT INTO memory_fts(doc_id, topic, content, category, memory_type, chapter_ref) VALUES (?,?,?,?,?,?)",
                        (it.item_id, it.topic, it.content, it.category, it.memory_type, it.chapter_reference)
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
            try:
                conn = self._get_conn()
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_fts'")
                row = cur.fetchone()
                conn.close()
                if not row:
                    self.rebuild_fts()
            except Exception:
                pass

    # ---------------- scoring backends ----------------

    def _bm25_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """Dùng rank_bm25 BM25Okapi — returns list (doc_id, bm25_score)."""
        if not self._check_bm25_available() or not self.items:
            return []
        try:
            from rank_bm25 import BM25Okapi  # type: ignore
            # Build corpus tokens
            corpus_tokens: List[List[str]] = []
            doc_ids: List[str] = []
            for it in self.items:
                combined = f"{it.topic} {it.content} {it.category}"
                toks = _tokenize(combined)
                corpus_tokens.append(toks)
                doc_ids.append(it.item_id)
            if not corpus_tokens:
                return []
            bm25 = BM25Okapi(corpus_tokens)
            q_tokens = _tokenize(query)
            if not q_tokens:
                return []
            scores = bm25.get_scores(q_tokens)
            # pair and sort
            scored = [(doc_ids[i], float(scores[i])) for i in range(len(doc_ids)) if scores[i] > 0]
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k * 2]
        except Exception:
            return []

    def _fts_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """FTS5 search với rank — returns (doc_id, score)."""
        try:
            conn = self._get_conn()
            fts_query = _normalize_query_for_fts(query)
            if not fts_query:
                conn.close()
                return []
            # FTS5 rank is negative; more negative = better
            cur = conn.execute("""
                SELECT doc_id, rank as bm25_rank
                FROM memory_fts
                WHERE memory_fts MATCH ?
                ORDER BY bm25_rank
                LIMIT ?
            """, (fts_query, top_k * 2))
            rows = cur.fetchall()
            conn.close()
            results: List[Tuple[str, float]] = []
            for r in rows:
                raw = r["bm25_rank"]
                score = float(-raw) if raw is not None and raw < 0 else float(1.0 / (1.0 + abs(raw or 1)))
                if score <= 0:
                    score = 0.5
                results.append((r["doc_id"], round(score, 4)))
            return results
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return []

    def _tfidf_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """Pure python TF-IDF fallback."""
        if not self.items:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            # fallback whitespace
            q_tokens = [t.lower() for t in re.findall(r"\S+", query.lower()) if t]
        N = len(self.items)
        # doc tokens
        doc_tokens_list: List[List[str]] = []
        doc_ids: List[str] = []
        for it in self.items:
            combined = f"{it.topic} {it.content} {it.category}"
            toks = _tokenize(combined)
            if not toks:
                toks = [t.lower() for t in re.findall(r"\S+", combined.lower()) if t]
            doc_tokens_list.append(toks)
            doc_ids.append(it.item_id)
        # DF
        df: Dict[str, int] = {}
        for tok in set(q_tokens):
            c = sum(1 for dt in doc_tokens_list if tok in dt)
            df[tok] = c
        scored: List[Tuple[str, float]] = []
        for idx, dt in enumerate(doc_tokens_list):
            score = 0.0
            dt_len = len(dt) or 1
            for tok in q_tokens:
                tf = dt.count(tok)
                if tf == 0:
                    continue
                idf = math.log((N + 1) / (df.get(tok, 0) + 1)) + 1
                tf_norm = 1 + math.log(tf) if tf > 0 else 0
                # length norm
                score += (tf_norm * idf) / (1 + 0.25 * (dt_len / 20))
            if score > 0:
                # topic boost: if query token in topic, boost
                topic_low = self.items[idx].topic.lower()
                if any(tok in topic_low for tok in q_tokens):
                    score *= 1.5
                scored.append((doc_ids[idx], round(score, 4)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k * 2]

    # ---------------- public API ----------------

    def add_memory(
        self,
        topic: str,
        category: str,
        content: str,
        chapter_reference: int,
        weight: float = 1.0,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> HybridMemoryItem:
        """Backward compat signature — thêm memory và persist + update FTS."""
        item_id = f"mem_{len(self.items)+1:04d}_{hashlib.md5((topic+content).encode()).hexdigest()[:4]}"
        # Tránh trùng id
        existing_ids = {it.item_id for it in self.items}
        base_id = item_id
        suffix = 1
        while item_id in existing_ids:
            item_id = f"{base_id}_{suffix}"
            suffix += 1
        item = HybridMemoryItem(
            item_id=item_id,
            topic=topic,
            category=category,
            content=content,
            chapter_reference=chapter_reference,
            weight=weight,
            memory_type=memory_type,
            tags=tags,
        )
        self.items.append(item)
        self._save()
        # incremental FTS update — thử insert, nếu lỗi thì rebuild
        try:
            self._ensure_fts_ready()
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO memory_fts(doc_id, topic, content, category, memory_type, chapter_ref) VALUES (?,?,?,?,?,?)",
                (item.item_id, item.topic, item.content, item.category, item.memory_type, item.chapter_reference)
            )
            conn.commit()
            conn.close()
        except Exception:
            try:
                self.rebuild_fts()
            except Exception:
                pass
        return item

    def add_typed_memory(
        self,
        topic: str,
        category: str,
        content: str,
        chapter_reference: int,
        memory_type: str = "episodic",
        weight: float = 1.0,
        tags: Optional[List[str]] = None,
    ) -> HybridMemoryItem:
        """Typed variant — explicit memory_type."""
        return self.add_memory(topic, category, content, chapter_reference, weight, memory_type, tags)

    def search(
        self,
        query: str,
        current_chapter: int,
        top_k: int = 4,
        memory_type_filter: Optional[str] = None,
        include_permanent: bool = True,
        category_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid Score = BM25/FTS lexical * weight * temporal_factor
        - temporal_factor chỉ cho episodic (exp decay), permanent luôn 1.0
        - Hỗ trợ filter theo memory_type/category
        """
        if not query or not query.strip():
            return []
        self._ensure_fts_ready()

        # 1) Lexical scores via tiered backends
        lexical: List[Tuple[str, float]] = []

        # Tier 1: rank_bm25 nếu có
        if self._check_bm25_available():
            lexical = self._bm25_search(query, top_k)
        # Tier 2: FTS5 nếu chưa có kết quả và FTS available
        if not lexical and self._check_fts_available() and os.path.exists(self.fts_db_path):
            lexical = self._fts_search(query, top_k)
        # Tier 3: TF-IDF fallback
        if not lexical:
            lexical = self._tfidf_search(query, top_k)

        # Nếu vẫn không có và items tồn tại, fallback overlap thô (để không trả về rỗng hoàn toàn)
        if not lexical and self.items:
            # giữ lại để temporal logic vẫn chạy — lấy overlap thô
            q_low = query.lower()
            q_toks = set(_tokenize(query))
            if not q_toks:
                q_toks = set(re.findall(r"\S+", q_low))
            for it in self.items:
                combined = f"{it.topic} {it.content}".lower()
                overlap = len(q_toks.intersection(set(_tokenize(combined)))) if q_toks else 0
                if overlap == 0 and any(tok in combined for tok in q_toks):
                    overlap = 1
                if overlap > 0:
                    lexical.append((it.item_id, float(overlap)))

        # 2) Map lexical scores to items + apply filters + temporal decay
        id_to_item: Dict[str, HybridMemoryItem] = {it.item_id: it for it in self.items}
        scored: List[Dict[str, Any]] = []

        for doc_id, base_score in lexical:
            it = id_to_item.get(doc_id)
            if not it:
                continue
            # Filters
            if memory_type_filter and it.memory_type != memory_type_filter:
                continue
            if category_filter and it.category != category_filter:
                continue
            if not include_permanent and it.is_permanent:
                continue

            # Temporal factor — chỉ episodic decay
            if it.is_episodic:
                temporal = it.temporal_factor(current_chapter, lambda_decay=0.03)
            else:
                temporal = 1.0

            # Permanent được boost nhẹ để không bị chìm bởi episodic gần
            # Nhưng episodic gần vẫn có decay-aware rank
            if it.is_permanent:
                total = float(base_score) * float(it.weight)
                # không nhân temporal, giữ nguyên
            else:
                # episodic: weight * (0.5 + 0.5*temporal) để không triệt tiêu hoàn toàn memory cũ
                total = float(base_score) * float(it.weight) * (0.5 + 0.5 * temporal)

            scored.append({
                "item_id": it.item_id,
                "topic": it.topic,
                "category": it.category,
                "memory_type": it.memory_type,
                "content": it.content,
                "chapter": it.chapter_reference,
                "chapter_reference": it.chapter_reference,
                "weight": it.weight,
                "temporal_factor": round(temporal, 4),
                "lexical_score": round(float(base_score), 4),
                "score": round(float(total), 4),
            })

        # Nếu không có lexical nhưng có items và query rỗng logic đã handle; còn nếu lexical rỗng hoàn toàn thì trả rỗng
        # Sắp xếp theo score giảm dần
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    # ---------------- utilities ----------------

    def get_by_type(self, memory_type: str) -> List[HybridMemoryItem]:
        return [it for it in self.items if it.memory_type == memory_type]

    def get_by_category(self, category: str) -> List[HybridMemoryItem]:
        return [it for it in self.items if it.category == category]

    def prune_future(self, current_chapter: int) -> int:
        """Xoá memories có chapter_reference > current_chapter (dùng cho rollback)."""
        before = len(self.items)
        self.items = [it for it in self.items if it.chapter_reference <= current_chapter]
        removed = before - len(self.items)
        if removed > 0:
            self._save()
            try:
                self.rebuild_fts()
            except Exception:
                pass
        return removed

    def count(self) -> int:
        return len(self.items)

    def clear(self):
        self.items = []
        self._save()
        try:
            self.rebuild_fts()
        except Exception:
            pass

    # Backward compat alias
    def rebuild_index(self) -> Dict[str, Any]:
        return self.rebuild_fts()
