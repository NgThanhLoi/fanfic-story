"""
P1.6 — Epistemic Ledger: (fact, known_by, since_chapter, secrecy) + visible_to(actor, canon_time)
"""
from typing import List, Dict, Set, Optional
from pydantic import BaseModel, Field
import pathlib, json

class KnowledgeFact(BaseModel):
    fact_id: str
    description: str = ""
    known_by: List[str] = Field(default_factory=list)  # entity_ids
    since_chapter: int = 1
    secrecy: str = "public"  # public, secret, forbidden

class EpistemicLedger(BaseModel):
    facts: Dict[str, KnowledgeFact] = Field(default_factory=dict)

    def learn(self, fact_id: str, actor: str, since_chapter: int, secrecy: str = "public", description: str = ""):
        if fact_id not in self.facts:
            self.facts[fact_id]=KnowledgeFact(fact_id=fact_id, description=description, known_by=[actor], since_chapter=since_chapter, secrecy=secrecy)
        else:
            f=self.facts[fact_id]
            if actor not in f.known_by: f.known_by.append(actor)
            f.since_chapter=min(f.since_chapter, since_chapter)

    def visible_to(self, actor: str, fact_id: str, canon_time: int) -> bool:
        f=self.facts.get(fact_id)
        if not f: return False
        if f.secrecy=="public": return canon_time >= f.since_chapter
        if f.secrecy=="forbidden": return False
        if actor not in f.known_by: return False
        return canon_time >= f.since_chapter

    def save(self, path: str):
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(path).write_text(json.dumps({k: v.model_dump() for k,v in self.facts.items()}, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "EpistemicLedger":
        data=json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return cls(facts={k: KnowledgeFact(**v) for k,v in data.items()})
