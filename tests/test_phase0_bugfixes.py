"""
Unit tests for Phase 0 bug fixes:
- P0-T1: DivergenceLedger.add_divergence produces ripples when bound
- P0-T2: mark_satisfied validates evidence against draft substring
- P0-T3: EpistemicLedger.visible_to allows public facts
- P0-T4: _check_frozen_canon is defined exactly once in matrix_33.py
- P0-T5: Fake checkers are marked status="stub" in CHECKER_REGISTRY
- P0-T6: hash_branch is evaluated in ConsistencyVerificationStack.evaluate
"""
import sys, pathlib, ast, inspect
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from fanfic_pipeline.butterfly.divergence_ledger import Divergence, DivergenceLedger
from fanfic_pipeline.butterfly.propagator import propagate
from fanfic_pipeline.butterfly.convergence import ButterflyPolicy
from fanfic_pipeline.butterfly.causal_graph import CausalGraph
from fanfic_pipeline.butterfly.pod import POD
from fanfic_pipeline.packages.canon.epistemic_ledger import EpistemicLedger, KnowledgeFact
from fanfic_pipeline.packages.auditor.matrix_33 import CHECKER_REGISTRY, ConsistencyVerificationStack
import fanfic_pipeline.packages.auditor.matrix_33 as matrix_33


class PropagatorShim:
    @staticmethod
    def propagate(pod, divergences, graph, policy, current_chapter=1):
        return propagate(pod, divergences, graph, policy, current_chapter)


def test_P0_T1_divergence_ledger_produces_ripples():
    """P0-T1: add_divergence() generates and returns ripples when bound."""
    ledger = DivergenceLedger()
    graph = CausalGraph(
        events={
            "EVT:001": {
                "id": "EVT:001",
                "actors": ["ENT:char:giang_chi_vi"],
                "scope": "personal",
                "preconditions": ["FACT:gcv_ignorant_luc_dao"],
                "necessity": "load_bearing",
                "canon_chapter": 18
            }
        },
        fact_to_events={"FACT:gcv_ignorant_luc_dao": ["EVT:001"]}
    )
    policy = ButterflyPolicy.default()
    pod = POD(
        id="POD:001",
        anchor_canon_chapter=18,
        statement="Mạnh Kỳ tiết lộ thân phận Lục Đạo cho Giang Chỉ Vi",
        author_intent="Đổi quan hệ"
    )
    ledger.bind(propagator=PropagatorShim, graph=graph, policy=policy, pod=pod)

    div = Divergence(
        id="DIV:001",
        fact="FACT:gcv_ignorant_luc_dao",
        op="retract",
        origin_fic_chapter=1
    )
    ripples = ledger.add_divergence(div)

    assert len(ripples) >= 1
    assert len(ledger.ripples) >= 1
    assert ripples[0].id.startswith("RIP:")
    assert ripples[0].from_divergence == "DIV:001"


def test_P0_T2_mark_satisfied_validation():
    """P0-T2: mark_satisfied checks evidence length and draft substring."""
    from fanfic_pipeline.butterfly.propagator import Ripple

    ledger = DivergenceLedger(
        ripples=[
            Ripple(
                id="RIP:001",
                from_divergence="DIV:001",
                tier=1,
                scope="personal",
                due_fic_chapter_range=[1, 3],
                status="open"
            )
        ]
    )

    draft = "Giang Chỉ Vi mỉm cười nói: Ngươi chính là truyền nhân Lục Đạo sao?"

    # Case 1: Evidence not in draft
    with pytest.raises(ValueError, match="substring"):
        ledger.mark_satisfied("RIP:001", 1, "Một đoạn văn không hề tồn tại", draft_text=draft)

    # Case 2: Evidence too short (< 5 chars)
    with pytest.raises(ValueError, match="at least 5"):
        ledger.mark_satisfied("RIP:001", 1, "abc", draft_text=draft)

    # Case 3: Valid evidence in draft
    ledger.mark_satisfied("RIP:001", 1, "truyền nhân Lục Đạo", draft_text=draft)
    assert ledger.ripples[0].status == "satisfied"


def test_P0_T3_epistemic_public_facts():
    """P0-T3: Public facts are visible to any actor when canon_time >= since_chapter."""
    ledger = EpistemicLedger()
    ledger.learn(
        fact_id="FACT:thieu_lam_mon_phai",
        actor="system",
        since_chapter=1,
        secrecy="public",
        description="Thiếu Lâm Tự là đại phái danh tiếng"
    )

    # Any character can see public facts
    assert ledger.visible_to("manh_ky", "FACT:thieu_lam_mon_phai", canon_time=5) is True
    assert ledger.visible_to("random_passerby", "FACT:thieu_lam_mon_phai", canon_time=1) is True
    # Before chapter 1, not visible
    assert ledger.visible_to("manh_ky", "FACT:thieu_lam_mon_phai", canon_time=0) is False

    # Secret facts still require explicit known_by
    ledger.learn(
        fact_id="FACT:bi_mat_ma_mon",
        actor="co_tieu_tang",
        since_chapter=10,
        secrecy="secret",
        description="Bí mật ma môn"
    )
    assert ledger.visible_to("co_tieu_tang", "FACT:bi_mat_ma_mon", canon_time=15) is True
    assert ledger.visible_to("manh_ky", "FACT:bi_mat_ma_mon", canon_time=15) is False


def test_P0_T4_frozen_canon_single_definition():
    """P0-T4: _check_frozen_canon is defined exactly once in matrix_33.py."""
    source = inspect.getsource(matrix_33)
    tree = ast.parse(source)
    func_defs = [
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_check_frozen_canon"
    ]
    assert len(func_defs) == 1, f"Expected 1 definition of _check_frozen_canon, found {len(func_defs)}"


def test_P0_T5_fake_checkers_marked_stub():
    """P0-T5: Fake pass checkers are marked as stub in CHECKER_REGISTRY."""
    stub_ids = {"ooc_fidelity", "relationship_dynamics", "pacing", "canon_fidelity"}
    registry_map = {spec.checker_id: spec for spec in CHECKER_REGISTRY}

    for cid in stub_ids:
        assert cid in registry_map, f"Checker {cid} must be present in CHECKER_REGISTRY"
        assert registry_map[cid].status == "stub", f"Checker {cid} must have status='stub', got {registry_map[cid].status}"


def test_P0_T6_hash_branch_in_evaluate():
    """P0-T6: hash_branch is evaluated and reported in ConsistencyVerificationStack.evaluate()."""
    receipt = ConsistencyVerificationStack.evaluate(
        packet_hash="test_packet",
        draft_text="Đây là bản nháp thử nghiệm có độ dài vừa đủ để vượt qua kiểm tra cơ bản về số lượng chữ của chương truyện.",
        outline={"chapter_number": 1, "scene_beats": []},
        audited_hash="a1b2c3d4e5f60718"
    )
    results_map = {r.checker_id: r for r in receipt.checker_results}
    assert "hash_branch" in results_map, "hash_branch must be included in audit results"
    assert results_map["hash_branch"].status == "PASS"
    assert "a1b2c3d4e5f60718" in results_map["hash_branch"].reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
