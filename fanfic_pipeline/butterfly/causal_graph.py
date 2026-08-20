"""
P2.2 — Causal Graph + Necessity labeling (SPEC §B2 preconditions + necessity)
- Each event has preconditions (fact_ids), necessity per precondition
- Out edges derived from shared facts
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import hashlib

class CausalEdge(BaseModel):
    src: str
    dst: str
    strength: float = 0.9
    necessity: str = "contingent"  # of dst's precondition

class CausalGraph(BaseModel):
    events: Dict[str, Any] = Field(default_factory=dict)  # event_id -> event
    edges: List[CausalEdge] = Field(default_factory=list)
    fact_to_events: Dict[str, List[str]] = Field(default_factory=dict)  # fact -> event_ids depending on it

    def depends_on_fact(self, fact_id: str) -> List[str]:
        return self.fact_to_events.get(fact_id, [])

    def out_edges(self, event_id: str) -> List[CausalEdge]:
        return [e for e in self.edges if e.src == event_id]

    def necessity_of_precondition(self, event_id: str, fact_id: str) -> str:
        ev = self.events.get(event_id, {})
        # heuristic: if fact in preconditions and event is load_bearing -> load_bearing
        pre = ev.get("preconditions", []) if isinstance(ev, dict) else getattr(ev, "preconditions", [])
        nec = ev.get("necessity", "contingent") if isinstance(ev, dict) else getattr(ev, "necessity", "contingent")
        if fact_id in pre:
            return nec
        return "contingent"

    @classmethod
    def from_events(cls, events: List[Any]) -> "CausalGraph":
        g = cls()
        for ev in events:
            eid = ev.event_id if hasattr(ev, "event_id") else ev.get("event_id")
            g.events[eid] = ev.model_dump() if hasattr(ev, "model_dump") else ev
            for fact in (ev.preconditions if hasattr(ev, "preconditions") else ev.get("preconditions", [])):
                g.fact_to_events.setdefault(fact, []).append(eid)
        # Build edges: if B's precondition is a fact produced by A's effect (heuristic: shared actor+temporal)
        evs = sorted(events, key=lambda e: (e.canon_chapter if hasattr(e,"canon_chapter") else e.get("canon_chapter",0)))
        for i,a in enumerate(evs):
            for b in evs[i+1:]:
                a_actors = set(a.actors if hasattr(a,"actors") else a.get("actors",[]))
                b_actors = set(b.actors if hasattr(b,"actors") else b.get("actors",[]))
                b_pre = b.preconditions if hasattr(b,"preconditions") else b.get("preconditions",[])
                a_eff = a.effects if hasattr(a,"effects") else a.get("effects",[])
                # Simple: shared actor within 10 chapters -> edge
                if (a_actors & b_actors) and abs((a.canon_chapter if hasattr(a,"canon_chapter") else 0) - (b.canon_chapter if hasattr(b,"canon_chapter") else 0)) <= 15:
                    eid_a = a.event_id if hasattr(a,"event_id") else a.get("event_id")
                    eid_b = b.event_id if hasattr(b,"event_id") else b.get("event_id")
                    g.edges.append(CausalEdge(src=eid_a, dst=eid_b, strength=0.7, necessity=b.necessity if hasattr(b,"necessity") else "contingent"))
        return g
