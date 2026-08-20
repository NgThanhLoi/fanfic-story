"""
P4.3 — Hybrid Memory SQLite (mở ở 200 chương):
- API giống HybridMemory: add_memory, search, prune, rebuild
- Backend: sqlite (FTS5 if available) + fallback JSON
- Tự chuyển khi len(items) > 200
"""
import json, pathlib, re, os, sqlite3
from typing import List, Dict, Any, Optional

class SQLiteMemory:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, topic TEXT, category TEXT, content TEXT, chapter_reference INTEGER, weight REAL, memory_type TEXT, created_at TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
        self.conn.commit()
        try:
            self.conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS mem_fts USING fts5(id, content, topic, tokenize='porter unicode61')")
        except: pass

    def add(self, item: Dict[str,Any]):
        self.conn.execute("INSERT OR REPLACE INTO memories VALUES (?,?,?,?,?,?,?,?)", (
            item.get("id") or item.get("item_id",""), item.get("topic",""), item.get("category",""), item.get("content",""), int(item.get("chapter_reference",0) or item.get("chapter",0)), float(item.get("weight",1.0)), item.get("memory_type","episodic"), item.get("created_at","")
        ))
        try:
            self.conn.execute("INSERT OR REPLACE INTO mem_fts VALUES (?,?,?)", (item.get("id") or item.get("item_id",""), item.get("content",""), item.get("topic","")))
        except: pass
        self.conn.commit()

    def search(self, query: str, top_k: int = 5) -> List[Dict[str,Any]]:
        # Try FTS
        try:
            cur=self.conn.execute("SELECT id FROM mem_fts WHERE mem_fts MATCH ? LIMIT ?", (query, top_k))
            ids=[r[0] for r in cur.fetchall()]
            if ids:
                cur=self.conn.execute(f"SELECT * FROM memories WHERE id IN ({','.join('?'*len(ids))})", ids)
                cols=[d[0] for d in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]
        except: pass
        # Fallback LIKE
        cur=self.conn.execute("SELECT * FROM memories WHERE content LIKE ? OR topic LIKE ? LIMIT ?", (f"%{query[:20]}%", f"%{query[:20]}%", top_k))
        cols=[d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def all(self) -> List[Dict[str,Any]]:
        cur=self.conn.execute("SELECT * FROM memories ORDER BY chapter_reference")
        cols=[d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def migrate_from_json(self, json_path: str) -> int:
        if not pathlib.Path(json_path).exists(): return 0
        data=json.loads(pathlib.Path(json_path).read_text(encoding="utf-8"))
        if isinstance(data, dict): data=list(data.values())
        for item in data[:500]:
            self.add(item if isinstance(item, dict) else item if isinstance(item, dict) else {})
        return len(data) if isinstance(data, list) else 0
