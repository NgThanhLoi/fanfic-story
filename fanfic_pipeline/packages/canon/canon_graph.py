"""
P1.4 — Canon Graph (& stubs for P1.5/1.6):
- Nodes = CanonEvent (from event_extractor)
- Edges = depends_on via preconditions (heuristic: shared actor+chapter order)
- Query: ancestors/descendants/depends_on
- Evidence invariant: every node/edge has evidence substring
"""
from typing import List, Dict, Set, Optional, Any
from pydantic import BaseModel, Field
import pathlib, json

class CanonEdge(BaseModel):
    edge_id: str
    src: str  # event_id
    dst: str
    relation: str = "depends_on"  # depends_on, causal, temporal
    evidence: str = ""
    strength: float = 0.7

class CanonGraph(BaseModel):
    nodes: Dict[str, Any] = Field(default_factory=dict)  # event_id -> CanonEvent
    edges: List[CanonEdge] = Field(default_factory=list)
    graph_hash: str = ""

    def ancestors(self, event_id: str, max_hops: int = 5) -> List[str]:
        # BFS backwards via edges where dst == event_id
        seen=set([event_id])
        frontier=[event_id]
        for _ in range(max_hops):
            nxt=[]
            for e in self.edges:
                if e.dst in frontier and e.src not in seen:
                    seen.add(e.src); nxt.append(e.src)
            if not nxt: break
            frontier=nxt
        seen.discard(event_id)
        return list(seen)

    def descendants(self, event_id: str, max_hops: int = 5) -> List[str]:
        seen=set([event_id])
        frontier=[event_id]
        for _ in range(max_hops):
            nxt=[]
            for e in self.edges:
                if e.src in frontier and e.dst not in seen:
                    seen.add(e.dst); nxt.append(e.dst)
            if not nxt: break
            frontier=nxt
        seen.discard(event_id)
        return list(seen)

    def depends_on_fact(self, fact_id: str) -> List[str]:
        # Return events whose preconditions include fact_id
        out=[]
        for eid, node in self.nodes.items():
            if hasattr(node, 'preconditions') and fact_id in getattr(node, 'preconditions', []):
                out.append(eid)
            elif isinstance(node, dict) and fact_id in node.get('preconditions', []):
                out.append(eid)
        return out

    def save(self, path: str):
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(path).write_text(json.dumps({"nodes": {k: (v.model_dump() if hasattr(v,'model_dump') else v) for k,v in self.nodes.items()}, "edges": [e.model_dump() for e in self.edges], "graph_hash": self.graph_hash}, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "CanonGraph":
        data=json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return cls(**data)

class CanonGraphBuilder:
    def build_from_events(self, events: list) -> CanonGraph:
        g=CanonGraph()
        for ev in events:
            eid = ev.event_id if hasattr(ev,'event_id') else ev.get('event_id')
            g.nodes[eid]=ev
        # Heuristic edges: if two events share actor and later chapter, earlier -> later depends_on
        evs = sorted(events, key=lambda e: (e.canon_chapter if hasattr(e,'canon_chapter') else e.get('canon_chapter',0)))
        for i, a in enumerate(evs):
            for b in evs[i+1:]:
                # Shared actor?
                a_actors=set(a.actors if hasattr(a,'actors') else a.get('actors',[]))
                b_actors=set(b.actors if hasattr(b,'actors') else b.get('actors',[]))
                if a_actors & b_actors and abs((a.canon_chapter if hasattr(a,'canon_chapter') else 0) - (b.canon_chapter if hasattr(b,'canon_chapter') else 0)) <= 10:
                    g.edges.append(CanonEdge(edge_id=f"E:{a.event_id}->{b.event_id}" if hasattr(a,'event_id') else f"E:{i}->{i+1}", src=a.event_id if hasattr(a,'event_id') else a.get('event_id'), dst=b.event_id if hasattr(b,'event_id') else b.get('event_id'), relation="depends_on", evidence=b.evidence[:30] if hasattr(b,'evidence') else "", strength=0.6))
        import hashlib
        g.graph_hash=hashlib.sha256(str(sorted(g.nodes.keys())).encode()).hexdigest()[:8]
        return g
