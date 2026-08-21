"""
P2 — Truy hồi canon tiếng Việt: FTS5 chuẩn-hóa-không-dấu + BM25 (nợ D6).

Corpus: data/nhat_the_chi_ton/vi_canon/chunks.jsonl (13.502 chunks / 1.397 chương).
Query có dấu hay không dấu cho evidence tương đương — hết nợ D6 của PLAN v2.0.
"""
import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

_DEFAULT_CORPUS = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "nhat_the_chi_ton", "vi_canon"))

_STRIP_MAP_SRC = ("áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợ"
                  "úùủũụưứừửữựýỳỷỹỵđ"
                  "ÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ")


def _strip_map() -> Dict[int, str]:
    out = {}
    for ch in _STRIP_MAP_SRC:
        base = "".join(c for c in unicodedata.normalize("NFD", ch)
                       if unicodedata.category(c) != "Mn").lower()
        out[ord(ch)] = base or ch.lower()
    return out


_STRIP = _strip_map()


def strip_diacritics(text: str) -> str:
    return text.translate(_STRIP)


_TOKEN_RE = re.compile(r"[a-z0-9àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]+")


def tokenize(text: str) -> List[str]:
    norm = strip_diacritics(text.lower())
    return _TOKEN_RE.findall(norm)


class ViCanonStore:
    """FTS5 index trên corpus VI. FTS query dùng token không dấu ⇒ query
    có-dấu/không-dấu cho kết quả như nhau."""

    def __init__(self, corpus_dir: Optional[str] = None):
        self.corpus_dir = corpus_dir or _DEFAULT_CORPUS
        self.chunks_path = os.path.join(self.corpus_dir, "chunks.jsonl")
        self.db_path = os.path.join(self.corpus_dir, "vi_fts.db")
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_db()

    # ---- index ----
    def _conn_get(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_db(self) -> None:
        if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0:
            try:
                conn = self._conn_get()
                n = conn.execute("SELECT COUNT(*) FROM vi_chunks").fetchone()[0]
                if n > 0:
                    return
            except Exception:
                pass
        self.rebuild()

    def rebuild(self) -> int:
        conn = self._conn_get()
        conn.executescript("""
            DROP TABLE IF EXISTS vi_chunks;
            CREATE VIRTUAL TABLE vi_chunks USING fts5(
                chunk_id UNINDEXED, chapter_no UNINDEXED, chapter_id UNINDEXED,
                title, text, tokenize='unicode61'
            );
        """)
        n = 0
        with open(self.chunks_path, encoding="utf-8") as f:
            rows = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                rows.append((r["chunk_id"], r["global_chapter_no"], r["chapter_id"],
                             r.get("chapter_title_vi", ""), r["text"]))
                n += 1
                if len(rows) >= 2000:
                    conn.executemany("INSERT INTO vi_chunks VALUES (?,?,?,?,?)", rows)
                    rows.clear()
        if rows:
            conn.executemany("INSERT INTO vi_chunks VALUES (?,?,?,?,?)", rows)
        conn.commit()
        return n

    # ---- query ----
    def search(self, query: str, top_k: int = 5,
               as_of_chapter: Optional[int] = None) -> List[Dict[str, Any]]:
        """BM25 search; as_of_chapter chặn truy-hồi vượt mốc thời gian canon
        (temporal boundary — writer không được thấy chunk tương lai)."""
        toks = tokenize(query)
        if not toks:
            return []
        fts_query = " OR ".join(toks)
        sql = ("SELECT chunk_id, chapter_no, chapter_id, title, text, "
               "bm25(vi_chunks) AS rank FROM vi_chunks WHERE vi_chunks MATCH ? ")
        args: list = [fts_query]
        if as_of_chapter is not None:
            sql += "AND chapter_no <= ? "
            args.append(as_of_chapter)
        sql += "ORDER BY rank LIMIT ?"
        args.append(top_k)
        conn = self._conn_get()
        out = []
        for row in conn.execute(sql, args):
            full_text = row["text"]
            # evidence-substring: trả về nguyên văn chunk (không paraphrase)
            out.append({
                "chunk_id": row["chunk_id"],
                "chapter_no": row["chapter_no"],
                "chapter_id": row["chapter_id"],
                "title": row["title"],
                "text": full_text,
                "score": round(-row["rank"], 4),
            })
        return out


def close() -> None:
    pass
