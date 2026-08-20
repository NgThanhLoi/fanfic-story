"""
P1.8 — Enrichment Store: SQLite-backed persistent repository for structured and semantic canon knowledge.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
import sqlite3, json, pathlib, os

class EnrichedEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    canonical_name: str
    aliases: List[str] = Field(default_factory=list)
    first_seen_chapter: int = 1
    mention_count: int = 1
    entity_type: str = "character"  # character, location, technique, sect, item, realm
    evidence: str = ""
    source_chapter: int = 1
    confidence: float = 1.0

class EnrichedRelationship(BaseModel):
    model_config = ConfigDict(extra="ignore")
    from_entity: str
    to_entity: str
    type: str  # master_student, ally, adversary, romantic, faction_member, rival
    since_chapter: int = 1
    evidence: str = ""
    confidence: float = 0.8

class EnrichedCausalLink(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cause_event: str
    effect_event: str
    necessity: str = "contingent"  # load_bearing, contingent, incidental
    evidence: str = ""
    confidence: float = 0.8

class EpistemicRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    character: str
    fact_id: str
    knows: bool = True
    since_chapter: int = 1
    until_chapter: Optional[int] = None
    evidence: str = ""

class ArcSummaryRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    window_id: int
    start_chapter: int
    end_chapter: int
    summary_text: str
    major_events: List[str] = Field(default_factory=list)
    active_characters: List[str] = Field(default_factory=list)

class EnrichmentStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                canonical_name TEXT NOT NULL,
                aliases TEXT NOT NULL,
                first_seen_chapter INTEGER NOT NULL,
                mention_count INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                evidence TEXT,
                source_chapter INTEGER,
                confidence REAL
            );
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(canonical_name);

            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity TEXT NOT NULL,
                to_entity TEXT NOT NULL,
                type TEXT NOT NULL,
                since_chapter INTEGER NOT NULL,
                evidence TEXT,
                confidence REAL,
                UNIQUE(from_entity, to_entity, type)
            );
            CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_entity);
            CREATE INDEX IF NOT EXISTS idx_rel_to ON relationships(to_entity);

            CREATE TABLE IF NOT EXISTS causal_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cause_event TEXT NOT NULL,
                effect_event TEXT NOT NULL,
                necessity TEXT NOT NULL,
                evidence TEXT,
                confidence REAL,
                UNIQUE(cause_event, effect_event)
            );

            CREATE TABLE IF NOT EXISTS epistemic_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character TEXT NOT NULL,
                fact_id TEXT NOT NULL,
                knows INTEGER NOT NULL,
                since_chapter INTEGER NOT NULL,
                until_chapter INTEGER,
                evidence TEXT,
                UNIQUE(character, fact_id, since_chapter)
            );
            CREATE INDEX IF NOT EXISTS idx_epistemic_char ON epistemic_records(character);

            CREATE TABLE IF NOT EXISTS arc_summaries (
                window_id INTEGER PRIMARY KEY,
                start_chapter INTEGER NOT NULL,
                end_chapter INTEGER NOT NULL,
                summary_text TEXT NOT NULL,
                major_events TEXT NOT NULL,
                active_characters TEXT NOT NULL
            );
            """)

    def add_entities(self, entities: List[EnrichedEntity]):
        with self._get_conn() as conn:
            for e in entities:
                row = conn.execute("SELECT aliases, first_seen_chapter, mention_count FROM entities WHERE id = ?", (e.id,)).fetchone()
                if row:
                    existing_aliases = set(json.loads(row["aliases"]))
                    existing_aliases.update(e.aliases)
                    new_first_seen = min(row["first_seen_chapter"], e.first_seen_chapter)
                    new_count = row["mention_count"] + e.mention_count
                    conn.execute("""
                        UPDATE entities
                        SET aliases = ?, first_seen_chapter = ?, mention_count = ?, confidence = MAX(confidence, ?)
                        WHERE id = ?
                    """, (json.dumps(list(existing_aliases), ensure_ascii=False), new_first_seen, new_count, e.confidence, e.id))
                else:
                    conn.execute("""
                        INSERT INTO entities (id, canonical_name, aliases, first_seen_chapter, mention_count, entity_type, evidence, source_chapter, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (e.id, e.canonical_name, json.dumps(e.aliases, ensure_ascii=False), e.first_seen_chapter, e.mention_count, e.entity_type, e.evidence, e.source_chapter, e.confidence))

    def add_relationships(self, rels: List[EnrichedRelationship]):
        with self._get_conn() as conn:
            for r in rels:
                conn.execute("""
                    INSERT INTO relationships (from_entity, to_entity, type, since_chapter, evidence, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(from_entity, to_entity, type) DO UPDATE SET
                        since_chapter = MIN(since_chapter, excluded.since_chapter),
                        confidence = MAX(confidence, excluded.confidence),
                        evidence = CASE WHEN length(evidence) > 0 THEN evidence ELSE excluded.evidence END
                """, (r.from_entity, r.to_entity, r.type, r.since_chapter, r.evidence, r.confidence))

    def add_causal_links(self, links: List[EnrichedCausalLink]):
        with self._get_conn() as conn:
            for link in links:
                conn.execute("""
                    INSERT INTO causal_links (cause_event, effect_event, necessity, evidence, confidence)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(cause_event, effect_event) DO UPDATE SET
                        necessity = excluded.necessity,
                        confidence = MAX(confidence, excluded.confidence)
                """, (link.cause_event, link.effect_event, link.necessity, link.evidence, link.confidence))

    def add_epistemic(self, records: List[EpistemicRecord]):
        with self._get_conn() as conn:
            for rec in records:
                conn.execute("""
                    INSERT INTO epistemic_records (character, fact_id, knows, since_chapter, until_chapter, evidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(character, fact_id, since_chapter) DO UPDATE SET
                        knows = excluded.knows,
                        until_chapter = excluded.until_chapter,
                        evidence = excluded.evidence
                """, (rec.character, rec.fact_id, 1 if rec.knows else 0, rec.since_chapter, rec.until_chapter, rec.evidence))

    def add_arc_summary(self, summary: ArcSummaryRecord):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO arc_summaries (window_id, start_chapter, end_chapter, summary_text, major_events, active_characters)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(window_id) DO UPDATE SET
                    start_chapter = excluded.start_chapter,
                    end_chapter = excluded.end_chapter,
                    summary_text = excluded.summary_text,
                    major_events = excluded.major_events,
                    active_characters = excluded.active_characters
            """, (summary.window_id, summary.start_chapter, summary.end_chapter, summary.summary_text, json.dumps(summary.major_events, ensure_ascii=False), json.dumps(summary.active_characters, ensure_ascii=False)))

    def query_entity(self, name_or_alias: str) -> Optional[EnrichedEntity]:
        with self._get_conn() as conn:
            # Check by exact canonical name or id
            row = conn.execute("SELECT * FROM entities WHERE id = ? OR canonical_name = ?", (name_or_alias, name_or_alias)).fetchone()
            if row:
                return EnrichedEntity(
                    id=row["id"], canonical_name=row["canonical_name"],
                    aliases=json.loads(row["aliases"]), first_seen_chapter=row["first_seen_chapter"],
                    mention_count=row["mention_count"], entity_type=row["entity_type"],
                    evidence=row["evidence"], source_chapter=row["source_chapter"],
                    confidence=row["confidence"]
                )
            # Scan aliases JSON
            rows = conn.execute("SELECT * FROM entities").fetchall()
            for r in rows:
                aliases = json.loads(r["aliases"])
                if name_or_alias in aliases:
                    return EnrichedEntity(
                        id=r["id"], canonical_name=r["canonical_name"],
                        aliases=aliases, first_seen_chapter=r["first_seen_chapter"],
                        mention_count=r["mention_count"], entity_type=r["entity_type"],
                        evidence=r["evidence"], source_chapter=r["source_chapter"],
                        confidence=r["confidence"]
                    )
        return None

    def query_all_entities(self, entity_type: Optional[str] = None) -> List[EnrichedEntity]:
        with self._get_conn() as conn:
            if entity_type:
                rows = conn.execute("SELECT * FROM entities WHERE entity_type = ? ORDER BY mention_count DESC", (entity_type,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM entities ORDER BY mention_count DESC").fetchall()
            return [
                EnrichedEntity(
                    id=r["id"], canonical_name=r["canonical_name"],
                    aliases=json.loads(r["aliases"]), first_seen_chapter=r["first_seen_chapter"],
                    mention_count=r["mention_count"], entity_type=r["entity_type"],
                    evidence=r["evidence"], source_chapter=r["source_chapter"],
                    confidence=r["confidence"]
                ) for r in rows
            ]

    def query_relationships(self, entity_id: str) -> List[EnrichedRelationship]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM relationships WHERE from_entity = ? OR to_entity = ?", (entity_id, entity_id)).fetchall()
            return [
                EnrichedRelationship(
                    from_entity=r["from_entity"], to_entity=r["to_entity"],
                    type=r["type"], since_chapter=r["since_chapter"],
                    evidence=r["evidence"], confidence=r["confidence"]
                ) for r in rows
            ]

    def query_causal_links(self) -> List[EnrichedCausalLink]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM causal_links").fetchall()
            return [
                EnrichedCausalLink(
                    cause_event=r["cause_event"], effect_event=r["effect_event"],
                    necessity=r["necessity"], evidence=r["evidence"],
                    confidence=r["confidence"]
                ) for r in rows
            ]

    def query_epistemic(self, character: Optional[str] = None) -> List[EpistemicRecord]:
        with self._get_conn() as conn:
            if character:
                rows = conn.execute("SELECT * FROM epistemic_records WHERE character = ?", (character,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM epistemic_records").fetchall()
            return [
                EpistemicRecord(
                    character=r["character"], fact_id=r["fact_id"],
                    knows=bool(r["knows"]), since_chapter=r["since_chapter"],
                    until_chapter=r["until_chapter"], evidence=r["evidence"]
                ) for r in rows
            ]

    def query_arc_summaries(self) -> List[ArcSummaryRecord]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM arc_summaries ORDER BY window_id ASC").fetchall()
            return [
                ArcSummaryRecord(
                    window_id=r["window_id"], start_chapter=r["start_chapter"],
                    end_chapter=r["end_chapter"], summary_text=r["summary_text"],
                    major_events=json.loads(r["major_events"]), active_characters=json.loads(r["active_characters"])
                ) for r in rows
            ]

    def stats(self) -> Dict[str, int]:
        with self._get_conn() as conn:
            return {
                "entities": conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
                "relationships": conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0],
                "causal_links": conn.execute("SELECT COUNT(*) FROM causal_links").fetchone()[0],
                "epistemic_records": conn.execute("SELECT COUNT(*) FROM epistemic_records").fetchone()[0],
                "arc_summaries": conn.execute("SELECT COUNT(*) FROM arc_summaries").fetchone()[0]
            }

    def export_json(self, path: str):
        data = {
            "entities": [e.model_dump() for e in self.query_all_entities()],
            "relationships": [r.model_dump() for r in self.query_relationships("")],
            "causal_links": [c.model_dump() for c in self.query_causal_links()],
            "epistemic": [p.model_dump() for p in self.query_epistemic()],
            "arc_summaries": [a.model_dump() for a in self.query_arc_summaries()]
        }
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def import_json(self, path: str):
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        if "entities" in data:
            self.add_entities([EnrichedEntity(**e) for e in data["entities"]])
        if "relationships" in data:
            self.add_relationships([EnrichedRelationship(**r) for r in data["relationships"]])
        if "causal_links" in data:
            self.add_causal_links([EnrichedCausalLink(**c) for c in data["causal_links"]])
        if "epistemic" in data:
            self.add_epistemic([EpistemicRecord(**p) for p in data["epistemic"]])
        if "arc_summaries" in data:
            for a in data["arc_summaries"]:
                self.add_arc_summary(ArcSummaryRecord(**a))
