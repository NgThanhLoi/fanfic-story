import pytest, tempfile, os
from fanfic_pipeline.butterfly.pod import POD, ChangedFact
from fanfic_pipeline.butterfly.propagator import propagate, ripples_from
from fanfic_pipeline.butterfly.convergence import ButterflyPolicy
from fanfic_pipeline.butterfly.divergence_ledger import Divergence
from fanfic_pipeline.butterfly.counterfactual import CounterfactualCache
from fanfic_pipeline.packages.canon.canon_graph_v2 import CanonGraphV2
from fanfic_pipeline.packages.enrichment.enrichment_store import EnrichmentStore, EnrichedCausalLink

def test_P4_T1_canon_graph_v2_import():
    tmp_dir = tempfile.mkdtemp()
    store = EnrichmentStore(os.path.join(tmp_dir, "test.db"))
    store.add_causal_links([
        EnrichedCausalLink(cause_event="EV_A", effect_event="EV_B", necessity="load_bearing", confidence=0.9)
    ])
    g = CanonGraphV2()
    g.sync_from_enrichment(store)
    assert len(g.edges) == 1
    assert g.edges[0].src == "EV_A"
    assert g.edges[0].dst == "EV_B"
    assert g.edges[0].necessity == "load_bearing"

def test_P4_T2_propagator_violates_protected():
    graph = CanonGraphV2()
    graph.events["EV_1"] = {"scope": "world", "actors": ["Nguyên Thủy Thiên Tôn"], "preconditions": ["FACT:ancient_past"]}
    graph.events["EV_2"] = {"scope": "personal", "actors": ["Mạnh Kỳ"], "preconditions": ["FACT:lost_fact"]}
    graph.fact_to_events["FACT:lost_fact"] = ["EV_2"]

    pod = POD(
        anchor_chapter=10,
        what_if_premise="Test",
        changed_facts=[ChangedFact(fact="FACT:lost_fact", op="retract")],
        protected_invariants=["Nguyên Thủy Thiên Tôn"]
    )
    policy = ButterflyPolicy.default()
    div = Divergence(id="DIV:001", fact="FACT:lost_fact", op="retract", origin_fic_chapter=10)

    status = propagate(pod, [div], graph, policy)

    assert status.get("EV_2").status == "cannot_happen" or status.get("EV_2").status == "altered"

def test_P4_T3_ripples_from_with_div_id():
    graph = CanonGraphV2()
    graph.events["EV_X"] = {"scope": "local", "actors": ["Mạnh Kỳ"]}
    from fanfic_pipeline.butterfly.propagator import EventStatus
    status = {"EV_X": EventStatus(status="cannot_happen", depth=1, force=0.9, reason="Test")}
    policy = ButterflyPolicy.default()

    ripples = ripples_from(status, graph, policy, current_chapter=1, div_id="DIV:099")
    assert len(ripples) == 1
    assert ripples[0].from_divergence == "DIV:099"

def test_P4_T4_counterfactual_cache_incremental():
    from fanfic_pipeline.butterfly.propagator import EventStatus
    cache = CounterfactualCache()
    status = {"EV_1": EventStatus(status="cannot_happen", depth=1, force=0.8, reason="Lost")}
    cache.update_from_status(status)
    assert cache.status_of("EV_1") == "cannot_happen"
    assert "EV_1" in cache.cannot_happen()
