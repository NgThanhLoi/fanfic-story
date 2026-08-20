"""
P2.3 — Propagator BFS (SPEC §B3.1 pseudocode):
- INERTIA[scope] * inertia_gain, NECESSITY_TRANSMIT, damping, max_depth, threshold, protected_invariants
- Returns status dict + ripples
"""
from collections import deque
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from fanfic_pipeline.butterfly.convergence import ButterflyPolicy, INERTIA, NECESSITY_TRANSMIT

class EventStatus(BaseModel):
    status: str  # intact | weakened | altered | cannot_happen
    depth: int = 0
    force: float = 0.0
    reason: str = ""

class Ripple(BaseModel):
    id: str
    from_divergence: str
    tier: int
    scope: str
    expected_manifestation: str = ""
    affected_entities: List[str] = Field(default_factory=list)
    due_fic_chapter_range: List[int] = Field(default_factory=list)
    status: str = "open"  # open|due|satisfied|overdue|waived
    priority: float = 0.0
    decay: float = 0.0

def _due_window(depth: int, force: float, policy: ButterflyPolicy, current_chapter: int = 1) -> List[int]:
    base = {1: (0, 3), 2: (2, 8), 3: (5, 20)}.get(min(depth, 3), (5, 20))
    return [current_chapter + base[0], current_chapter + base[1]]

def propagate(pod, divergences: List[Any], graph, policy: ButterflyPolicy, current_chapter: int = 1) -> Dict[str, EventStatus]:
    status: Dict[str, EventStatus] = {}
    queue = deque()
    # Seed: events depending on fact being diverged
    for div in divergences:
        fact = div.fact if hasattr(div,'fact') else div.get('fact')
        intensity = getattr(div, 'intensity', pod.intensity if hasattr(pod,'intensity') else 0.7) if hasattr(div,'intensity') or hasattr(pod,'intensity') else 0.7
        # fact may be in changed_facts
        facts = [fact] if fact else ([f.fact for f in (pod.changed_facts if hasattr(pod,'changed_facts') else [])] if hasattr(pod,'changed_facts') else [])
        for fid in facts:
            for ev_id in graph.depends_on_fact(fid):
                queue.append((ev_id, 1, intensity, div))

    def holds_after(fact_id: str) -> bool:
        for div in divergences:
            f = div.fact if hasattr(div,'fact') else div.get('fact')
            op = div.op if hasattr(div,'op') else div.get('op')
            if f == fact_id:
                return op == 'assert'
        # Also check pod
        if hasattr(pod, 'changed_facts'):
            for cf in pod.changed_facts:
                if getattr(cf,'fact',None)==fact_id:
                    return getattr(cf,'op','assert')=='assert'
        return True  # default intact

    def violates_protected(ev_id: str) -> bool:
        if not hasattr(pod, 'protected_invariants') or not getattr(pod, 'protected_invariants', None):
            return False
        ev = graph.events.get(ev_id, {})
        ev_actors = set(ev.get('actors', []) if isinstance(ev, dict) else getattr(ev, 'actors', []))
        ev_pre = set(ev.get('preconditions', []) if isinstance(ev, dict) else getattr(ev, 'preconditions', []))
        for inv in pod.protected_invariants:
            if inv in ev_pre or any(inv in str(a) for a in ev_actors):
                return True
        return False

    while queue:
        ev_id, depth, force, src = queue.popleft()
        if depth > policy.max_depth: continue
        ev = graph.events.get(ev_id, {})
        scope = ev.get('scope','personal') if isinstance(ev, dict) else getattr(ev,'scope','personal')
        resist = INERTIA.get(scope, 0.35) * policy.inertia_gain
        effective = force * (1 - resist)
        if effective < policy.threshold: continue

        # Decide status based on lost preconditions
        pre = ev.get('preconditions', []) if isinstance(ev, dict) else getattr(ev,'preconditions',[])
        lost = [p for p in pre if not holds_after(p)]
        if any(graph.necessity_of_precondition(ev_id, p) == "load_bearing" for p in lost):
            new_status = "cannot_happen"
        elif lost:
            new_status = "altered" if effective > 0.4 else "weakened"
        else:
            new_status = "weakened" if effective < 0.5 else "intact"
            if new_status == "intact":
                status[ev_id] = EventStatus(status="intact", depth=depth, force=effective, reason="preconditions intact")
                continue

        if violates_protected(ev_id):
            new_status = "intact"
            status[ev_id] = EventStatus(status="intact", depth=depth, force=effective, reason="protected_invariant blocked")
            continue

        # Merge worse (cannot_happen > altered > weakened > intact)
        order = {"intact":0, "weakened":1, "altered":2, "cannot_happen":3}
        prev = status.get(ev_id)
        if prev and order.get(prev.status,0) >= order.get(new_status,0):
            continue
        status[ev_id] = EventStatus(status=new_status, depth=depth, force=effective, reason=f"depth{depth} force{effective:.2f}")

        if new_status != "intact":
            for edge in graph.out_edges(ev_id):
                transmit = NECESSITY_TRANSMIT.get(edge.necessity, 0.5)
                if transmit == 0.0: continue
                nxt = effective * edge.strength * transmit * policy.damping * policy.butterfly_gain
                queue.append((edge.dst, depth+1, nxt, ev_id))
    return status

def ripples_from(status: Dict[str, EventStatus], graph, policy: ButterflyPolicy, current_chapter: int = 1, div_id: Optional[str] = None) -> List[Ripple]:
    out=[]
    for ev_id, st in status.items():
        if st.status == "intact": continue
        ev = graph.events.get(ev_id, {})
        actors = ev.get('actors', []) if isinstance(ev, dict) else getattr(ev,'actors',[])
        scope = ev.get('scope','personal') if isinstance(ev, dict) else getattr(ev,'scope','personal')
        out.append(Ripple(
            id=f"RIP:{len(out)+1:03d}",
            from_divergence=div_id or "DIV:000",
            tier=min(st.depth, 3),
            scope=scope,
            expected_manifestation=f"Event {ev_id} is {st.status} (depth {st.depth})",
            affected_entities=actors,
            due_fic_chapter_range=_due_window(st.depth, st.force, policy, current_chapter),
            status="open",
            priority=st.force * (1.0 if st.status=="cannot_happen" else 0.6),
            decay=policy.damping ** st.depth,
        ))
    # Cap
    out.sort(key=lambda r: -r.priority)
    return out[:policy.max_open_ripples]

