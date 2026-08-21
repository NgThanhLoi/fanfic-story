"""
P4.3 — SQLite Memory Store:
Single-file SQLite backend replacing JSON + derived FTS index.
- memories table: authority data (replaces hybrid_memory.json)
- memory_fts: FTS5 virtual table (replaces .fts.db)
- Auto-migrate from JSON on first open if .db doesn't exist but .json does
- Same HybridMemoryItem model, zero API changes to HybridMemoryEngine
"""

import os
import json
import sqlite3
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


class SqliteMemoryStore:
    """
    SQLite-backed persistence for HybridMemoryItem.
    Replaces JSON file (_load/_save) + separate FTS DB (rebuild_fts).
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            # Check if already initialized
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
            )
            if cur.fetchone():
                return  # Already exists

            # Create memories table (authority)
            conn.execute("""
                CREATE TABLE memories (
                    item_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'episodic',
                    content TEXT NOT NULL DEFAULT '',
                    chapter_reference INTEGER NOT NULL DEFAULT 0,
                    weight REAL NOT NULL DEFAULT 1.0,
                    memory_type TEXT NOT NULL DEFAULT 'episodic',
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT '',
                    extra TEXT NOT NULL DEFAULT '{}'
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mem_chapter ON memories(chapter_reference)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mem_type ON memories(memory_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mem_category ON memories(category)"
            )

            # Create FTS5 virtual table
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE memory_fts USING fts5(
                        doc_id, topic, content, category, memory_type, chapter_ref,
                        tokenize='unicode61 remove_diacritics 0'
                    )
                """)
            except Exception:
                # Fallback without diacritics option
                try:
                    conn.execute("""
                        CREATE VIRTUAL TABLE memory_fts USING fts5(
                            doc_id, topic, content, category, memory_type, chapter_ref
                        )
                    """)
                except Exception:
                    # Ultimate fallback: plain table with LIKE
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
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_fts_content ON memory_fts(content)"
                    )

            # Schema version tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute(
                "INSERT OR REPLACE INTO _meta(key, value) VALUES ('schema_version', ?)",
                (str(self.SCHEMA_VERSION),),
            )
            conn.commit()
        finally:
            conn.close()

    # ---------------- CRUD ----------------

    def load_all(self) -> List[Dict[str, Any]]:
        """Load all memories as dicts (compatible with HybridMemoryItem.from_dict)."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT item_id, topic, category, content, chapter_reference, "
                "weight, memory_type, tags, created_at, extra FROM memories"
            ).fetchall()
            result = []
            for r in rows:
                result.append({
                    "item_id": r["item_id"],
                    "topic": r["topic"],
                    "category": r["category"],
                    "content": r["content"],
                    "chapter_reference": r["chapter_reference"],
                    "weight": r["weight"],
                    "memory_type": r["memory_type"],
                    "tags": json.loads(r["tags"]) if r["tags"] else [],
                    "created_at": r["created_at"],
                    "extra": json.loads(r["extra"]) if r["extra"] else {},
                })
            return result
        finally:
            conn.close()

    def save_all(self, items: List[Dict[str, Any]]):
        """Replace all memories (atomic). Used by _save() and migration."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM memories")
            conn.execute("DELETE FROM memory_fts")
            for it in items:
                tags_json = json.dumps(it.get("tags", []), ensure_ascii=False)
                extra_json = json.dumps(it.get("extra", {}), ensure_ascii=False)
                conn.execute(
                    "INSERT INTO memories(item_id, topic, category, content, "
                    "chapter_reference, weight, memory_type, tags, created_at, extra) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        it["item_id"],
                        it.get("topic", ""),
                        it.get("category", "episodic"),
                        it.get("content", ""),
                        int(it.get("chapter_reference", 0)),
                        float(it.get("weight", 1.0)),
                        it.get("memory_type", "episodic"),
                        tags_json,
                        it.get("created_at", ""),
                        extra_json,
                    ),
                )
                # Also insert into FTS
                try:
                    conn.execute(
                        "INSERT INTO memory_fts(doc_id, topic, content, category, memory_type, chapter_ref) "
                        "VALUES (?,?,?,?,?,?)",
                        (
                            it["item_id"],
                            it.get("topic", ""),
                            it.get("content", ""),
                            it.get("category", "episodic"),
                            it.get("memory_type", "episodic"),
                            int(it.get("chapter_reference", 0)),
                        ),
                    )
                except Exception:
                    pass
            conn.commit()
        finally:
            conn.close()

    def add_item(self, item_dict: Dict[str, Any]):
        """Insert single memory item + FTS entry."""
        conn = self._get_conn()
        try:
            tags_json = json.dumps(item_dict.get("tags", []), ensure_ascii=False)
            extra_json = json.dumps(item_dict.get("extra", {}), ensure_ascii=False)
            conn.execute(
                "INSERT OR REPLACE INTO memories(item_id, topic, category, content, "
                "chapter_reference, weight, memory_type, tags, created_at, extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    item_dict["item_id"],
                    item_dict.get("topic", ""),
                    item_dict.get("category", "episodic"),
                    item_dict.get("content", ""),
                    int(item_dict.get("chapter_reference", 0)),
                    float(item_dict.get("weight", 1.0)),
                    item_dict.get("memory_type", "episodic"),
                    tags_json,
                    item_dict.get("created_at", ""),
                    extra_json,
                ),
            )
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO memory_fts(doc_id, topic, content, category, memory_type, chapter_ref) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        item_dict["item_id"],
                        item_dict.get("topic", ""),
                        item_dict.get("content", ""),
                        item_dict.get("category", "episodic"),
                        item_dict.get("memory_type", "episodic"),
                        int(item_dict.get("chapter_reference", 0)),
                    ),
                )
            except Exception:
                pass
            conn.commit()
        finally:
            conn.close()

    def delete_items(self, item_ids: List[str]):
        """Delete memories by IDs."""
        if not item_ids:
            return
        conn = self._get_conn()
        try:
            placeholders = ",".join("?" * len(item_ids))
            conn.execute(f"DELETE FROM memories WHERE item_id IN ({placeholders})", item_ids)
            try:
                conn.execute(f"DELETE FROM memory_fts WHERE doc_id IN ({placeholders})", item_ids)
            except Exception:
                pass
            conn.commit()
        finally:
            conn.close()

    def prune_future(self, current_chapter: int) -> int:
        """Delete memories with chapter_reference > current_chapter. Returns count removed."""
        conn = self._get_conn()
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE chapter_reference > ?",
                (current_chapter,),
            )
            count = cur.fetchone()[0]
            if count > 0:
                conn.execute(
                    "DELETE FROM memories WHERE chapter_reference > ?",
                    (current_chapter,),
                )
                try:
                    conn.execute(
                        "DELETE FROM memory_fts WHERE chapter_ref > ?",
                        (current_chapter,),
                    )
                except Exception:
                    pass
                conn.commit()
            return count
        finally:
            conn.close()

    def clear_all(self):
        """Delete all memories and FTS entries."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM memories")
            try:
                conn.execute("DELETE FROM memory_fts")
            except Exception:
                pass
            conn.commit()
        finally:
            conn.close()

    def count(self) -> int:
        conn = self._get_conn()
        try:
            return conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        finally:
            conn.close()

    # ---------------- FTS search ----------------

    def fts_search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Search FTS index. Returns [(doc_id, score), ...]."""
        conn = self._get_conn()
        try:
            # Check if FTS5 or plain table
            cur = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='memory_fts'"
            )
            row = cur.fetchone()
            is_fts5 = row and "fts5" in (row[0] or "").lower()

            if is_fts5:
                try:
                    rows = conn.execute(
                        "SELECT doc_id, rank FROM memory_fts WHERE memory_fts MATCH ? ORDER BY rank LIMIT ?",
                        (query, top_k),
                    ).fetchall()
                    # FTS5 rank is negative (lower = better), negate for consistency
                    return [(r["doc_id"], -r["rank"]) for r in rows]
                except Exception:
                    pass

            # Fallback: LIKE search
            like_q = f"%{query}%"
            rows = conn.execute(
                "SELECT doc_id FROM memory_fts WHERE content LIKE ? OR topic LIKE ? LIMIT ?",
                (like_q, like_q, top_k),
            ).fetchall()
            return [(r["doc_id"], 1.0) for r in rows]
        finally:
            conn.close()

    def rebuild_fts(self) -> Dict[str, Any]:
        """Drop and rebuild FTS from memories table."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM memory_fts")
            rows = conn.execute(
                "SELECT item_id, topic, content, category, memory_type, chapter_reference FROM memories"
            ).fetchall()
            count = 0
            for r in rows:
                try:
                    conn.execute(
                        "INSERT INTO memory_fts(doc_id, topic, content, category, memory_type, chapter_ref) "
                        "VALUES (?,?,?,?,?,?)",
                        (r["item_id"], r["topic"], r["content"], r["category"], r["memory_type"], r["chapter_reference"]),
                    )
                    count += 1
                except Exception:
                    continue
            conn.commit()
            return {"status": "ok", "docs_indexed": count}
        finally:
            conn.close()

    # ---------------- Migration ----------------

    @staticmethod
    def migrate_from_json(json_path: str, db_path: str) -> int:
        """Migrate JSON file to SQLite. Returns count of migrated items."""
        if not os.path.exists(json_path):
            return 0
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = list(data.values())
            else:
                return 0

            store = SqliteMemoryStore(db_path)
            store.save_all(items)
            return len(items)
        except Exception:
            return 0
