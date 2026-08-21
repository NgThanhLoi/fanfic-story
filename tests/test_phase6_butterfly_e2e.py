"""
Phase 6 — Butterfly Effect Engine end-to-end integration (SPEC §6.2.5):
- Engine loads POD + DivergenceLedger + CounterfactualCache + CausalGraph from project dir
- build_sealed_packet injects ripples_due / forbidden / canon_time_max into packet
- run_chapter_step: extract divergence from draft → propagate → ripples → counterfactual refresh → persist
"""
import pytest, tempfile, os, json
from fanfic_pipeline.core.state_manager import ProjectStateManager
from fanfic_pipeline.core.engine import FanficEngine
from fanfic_pipeline.core.models import PointOfDivergence as LegacyPOD
from fanfic_pipeline.butterfly.pod import POD, ChangedFact
from fanfic_pipeline.packages.enrichment.enrichment_store import EnrichmentStore, EnrichedCausalLink


def _setup_project_with_butterfly(base_dir: str, project_id: str) -> str:
    """Tạo project có enrichment.db (causal link) + butterfly/pod.json (POD:001-like)."""
    mgr = ProjectStateManager(project_id=project_id, base_dir=base_dir)
    pod = LegacyPOD(
        divergence_anchor="Chương 1",
        what_if_premise="Mạnh Kỳ quyết định tu luyện Lôi Đao từ đầu.",
        butterfly_effects=[],
        frozen_canon=[]
    )
    mgr.init_project(title="Butterfly E2E", fandom="Nhất Thế Chi Tôn", pod=pod, voices={}, relationships=[])

    # enrichment.db — causal link: fact bị retract là precondition load_bearing của event
    db_path = os.path.join(mgr.project_dir, "enrichment.db")
    store = EnrichmentStore(db_path)
    store.add_causal_links([
        EnrichedCausalLink(
            cause_event="FACT:gcv_ignorant_luc_dao",
            effect_event="EVT:gcv_suspect",
            necessity="load_bearing",
            confidence=0.9
        )
    ])

    # butterfly/pod.json — POD:001 (retract gcv_ignorant_luc_dao)
    bf_dir = os.path.join(mgr.project_dir, "butterfly")
    os.makedirs(bf_dir, exist_ok=True)
    bpod = POD(
        id="POD:001",
        anchor_canon_chapter=18,
        statement="Tại canon ch.18, Mạnh Kỳ tiết lộ thân phận Lục Đạo Luân Hồi cho Giang Chỉ Vi",
        kind="epistemic",
        scope="personal",
        intensity=0.7,
        changed_facts=[
            ChangedFact(op="assert", fact="FACT:gcv_knows_luc_dao", at_fic_chapter=1),
            ChangedFact(op="retract", fact="FACT:gcv_ignorant_luc_dao", at_fic_chapter=1),
        ],
        protected_invariants=["INV:001"],
        author_intent="Đổi quan hệ Mạnh Kỳ - Giang Chỉ Vi, KHÔNG đổi cục diện Cửu Châu",
    )
    bpod.save(os.path.join(bf_dir, "pod.json"))
    return mgr.project_dir


def test_P6_T1_engine_loads_butterfly_state():
    tmp = tempfile.mkdtemp()
    project_dir = _setup_project_with_butterfly(tmp, "p6_load")
    mgr = ProjectStateManager(project_id="p6_load", base_dir=tmp)
    engine = FanficEngine(mgr)

    assert engine.butterfly_pod is not None
    assert engine.butterfly_pod.id == "POD:001"
    assert engine.ledger is not None
    assert engine.counterfactual is not None
    assert engine.butterfly_graph is not None
    assert len(engine.butterfly_graph.edges) == 1


def test_P6_T2_butterfly_lifecycle_propagates_and_persists():
    tmp = tempfile.mkdtemp()
    _setup_project_with_butterfly(tmp, "p6_life")
    mgr = ProjectStateManager(project_id="p6_life", base_dir=tmp)
    engine = FanficEngine(mgr)

    outline, draft, critique, delta = engine.run_chapter_step(chapter_num=1)

    # 1. Divergence được extract từ POD changed_facts + propagate sinh ripples
    assert len(engine.ledger.divergences) >= 1
    assert len(engine.ledger.ripples) >= 1
    # 2. Counterfactual có event cannot_happen (load_bearing precondition bị retract)
    assert len(engine.counterfactual.cannot_happen()) >= 1
    # 3. Butterfly state persisted ra đĩa
    bf_dir = os.path.join(mgr.project_dir, "butterfly")
    assert os.path.exists(os.path.join(bf_dir, "divergence_ledger.json"))
    assert os.path.exists(os.path.join(bf_dir, "counterfactual.json"))


def test_P6_T3_packet_injects_ripples_and_forbidden():
    tmp = tempfile.mkdtemp()
    _setup_project_with_butterfly(tmp, "p6_packet")
    mgr = ProjectStateManager(project_id="p6_packet", base_dir=tmp)
    engine = FanficEngine(mgr)

    # Chương 1: propagate sinh ripple với due window bắt đầu tại chương 1
    engine.run_chapter_step(chapter_num=1)
    assert len(engine.ledger.ripples) >= 1

    # Chương 2: packet phải chứa ripples_due + forbidden (cannot_happen) + canon_time_max
    packet = engine.build_sealed_packet(chapter_num=2)
    assert packet.canon_time_max == 2
    assert packet.forbidden  # counterfactual cannot_happen list không rỗng
    due = [r for r in engine.ledger.ripples if r.status == "open"]
    if due:
        assert packet.ripples_due  # ripple đang open và due window chứa chương 2


def test_P6_T4_graceful_without_butterfly():
    """Project không có POD/enrichment vẫn chạy bình thường (butterfly no-op)."""
    tmp = tempfile.mkdtemp()
    mgr = ProjectStateManager(project_id="p6_plain", base_dir=tmp)
    pod = LegacyPOD(
        divergence_anchor="Chương 1",
        what_if_premise="Test",
        butterfly_effects=[],
        frozen_canon=[]
    )
    mgr.init_project(title="Plain", fandom="Nhất Thế Chi Tôn", pod=pod, voices={}, relationships=[])
    engine = FanficEngine(mgr)

    assert engine.butterfly_pod is None
    assert engine.ledger is not None
    outline, draft, critique, delta = engine.run_chapter_step(chapter_num=1)
    assert draft.chapter_number == 1
    assert len(draft.content) > 100
