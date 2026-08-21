"""
P0 Governance — Test đối kháng (spec 2026-08-21 §6 P0).

Mỗi test bắn vào một invariant:
- INV-1: premise sai canon ⇒ readiness BLOCK (skip aperture, domain-fill TCM)
- INV-2: durable head single-source; event_map chain đứt ⇒ BLOCK
- INV-3: layer tắt phải ra ROUTED_OFF_WITH_REASON receipt
- INV-4: commit phải sinh event_map + manifest; doctor bắt manifest stale
- INV-5: audit --all derive từ committed chain, không hard-code range
- Fake-USED (USED không evidence) bị ComplianceReport.validate_complete + cmd_audit bắt
"""
import json
import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fanfic_pipeline.core.state_manager import ProjectStateManager
from fanfic_pipeline.core.models import (
    PointOfDivergence, ChapterDraft, ChapterOutline, SceneBeat,
)
from fanfic_pipeline.core.story_state import StateDelta
from fanfic_pipeline.packages.memory.hybrid_retriever import HybridMemoryEngine
from fanfic_pipeline.core.transaction_manager import ChapterTransactionManager
from fanfic_pipeline.packages.governance.policy import RuntimePolicy
from fanfic_pipeline.packages.governance.topology import load_default_topology
from fanfic_pipeline.packages.governance.premise import PremiseValidator
from fanfic_pipeline.packages.governance.readiness import ReadinessGate, save_readiness
from fanfic_pipeline.packages.governance.compliance import (
    ComplianceReport, SubsystemStatus, derive_chapter_numbers, SUBSYSTEMS,
)


@pytest.fixture()
def project():
    tmp = tempfile.mkdtemp(prefix="gov_test_")
    old = os.environ.get("FANFIC_STORAGE_DIR")
    os.environ["FANFIC_STORAGE_DIR"] = tmp
    try:
        mgr = ProjectStateManager("govadv")
        mgr.init_project(
            title="Gov Adversarial", fandom="Nhất Thế Chi Tôn",
            pod=PointOfDivergence(divergence_anchor="a", what_if_premise="p",
                                  butterfly_effects=[], frozen_canon=[]),
            voices={}, relationships=[], execution_mode="FULL_AUTO",
        )
        yield mgr
    finally:
        if old is None:
            os.environ.pop("FANFIC_STORAGE_DIR", None)
        else:
            os.environ["FANFIC_STORAGE_DIR"] = old
def _commit_ch(mgr: ProjectStateManager, ch: int, content: str = "Nội dung thử nghiệm cho chương.") -> dict:
    mem = HybridMemoryEngine(os.path.join(mgr.project_dir, "hybrid_memory.json"))
    tx = ChapterTransactionManager(mgr, mem)
    draft = ChapterDraft(chapter_number=ch, title=f"Chương {ch}", word_count=2,
                         content=content, summary="s")
    outline = ChapterOutline(
        chapter_number=ch, title=f"Chương {ch}", point_of_view="Mạnh Kỳ", core_conflict="c",
        scene_beats=[SceneBeat(beat_number=1, scene_type="action",
                               characters_present=["Mạnh Kỳ"], a_plot_goal="A",
                               b_plot_goal="B", key_event="K", tension_element="T")])
    h = mgr.calculate_draft_hash(draft.content)
    return tx.commit_transaction(ch, draft, outline, state_delta=StateDelta(chapter_number=ch),
                                 expected_hash=h)


# ---------------- topology / premise (INV-1) ----------------

class TestTopology:
    def test_legal_progression_passes(self):
        t = load_default_topology()
        assert t.validate_progression(["eye"], "ear") == []

    def test_illegal_skip_blocked(self):
        """Test B review §20: eye -> nose phải BLOCK_CANONICAL_TRANSITION."""
        t = load_default_topology()
        v = t.validate_progression(["eye"], "nose")
        assert any(x.kind == "skip_transition" for x in v)

    def test_exception_receipt_allows(self):
        t = load_default_topology()
        v = t.validate_progression(["eye"], "nose", exception_receipts=["exception:eye->nose"])
        assert v == []

    def test_domain_fill_tcm_blocked(self):
        """Review F-02: huyệt TCM điền vào khoảng trống canon phải bị chặn."""
        t = load_default_topology()
        v = t.validate_artifact("Ngưng tụ vào hai huyệt Nghênh Hương men theo Đốc Mạch", ["eye"])
        kinds = {x.kind for x in v}
        assert "domain_fill" in kinds

    def test_negation_not_treated_as_opening(self):
        t = load_default_topology()
        assert t.extract_opened("Bọn họ đều còn chưa khai nhĩ khiếu") == []

    def test_premise_validator_blocks_bad_spec(self):
        pv = PremiseValidator()
        receipt = pv.validate(committed_opened=["eye"], artifacts={
            "chapter_spec": "FC36: bước đầu ngưng tụ các huyệt đạo quanh Tỵ Khiếu, khiếu thứ hai"})
        assert not receipt.ok
        assert any(v["kind"] in ("skip_transition", "domain_fill") for v in receipt.violations)

    def test_premise_receipt_hash_stable(self):
        pv = PremiseValidator()
        r1 = pv.validate(["eye"], {"spec": "khai nhĩ khiếu"})
        r2 = pv.validate(["eye"], {"spec": "khai nhĩ khiếu"})
        assert r1.receipt_hash == r2.receipt_hash


# ---------------- readiness gate (INV-1, INV-2) ----------------

class TestReadinessGate:
    def test_block_when_sequentiality_violated(self, project):
        _commit_ch(project, 1)
        gate = ReadinessGate(project)
        r = gate.evaluate(3)  # nhảy cóc: head=1, yêu cầu 3
        assert r.verdict == "BLOCK"
        assert any(b["check"] == "sequential_commit" for b in r.blockers)

    def test_ready_on_clean_foundation(self, project):
        _commit_ch(project, 1)
        # canon đã ingest (foundation) + story state khai đúng aperture đã mở
        meta = project.load_project_meta()
        meta["canon_ingested"] = True
        project.update_project_meta(meta)
        state = project.load_story_state()
        state["opened_apertures"] = ["eye"]
        with open(project.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        gate = ReadinessGate(project)
        r = gate.evaluate(2, planning_artifacts={
            "chapter_spec": "Tiếp tục rèn đao ý; chuẩn bị khai nhĩ khiếu ở chương sau."})
        assert r.verdict == "READY", r.blockers
        assert r.premise is not None and r.premise.ok

    def test_block_on_bad_premise(self, project):
        _commit_ch(project, 1)
        gate = ReadinessGate(project)
        bad_spec = "Chương kế: ngưng luyện Tỵ Khiếu — khiếu thứ hai sau Nhãn Khiếu"
        r = gate.evaluate(2, planning_artifacts={"chapter_spec": bad_spec})
        assert r.verdict == "BLOCK"
        assert any(b["check"] == "premise_validation" for b in r.blockers)


# ---------------- policy (INV-3) ----------------

class TestPolicy:
    def test_disabled_layer_produces_receipt(self, project):
        pol = RuntimePolicy(project.project_dir)
        receipts = pol.routed_off_receipts()
        ids = {r["subsystem"] for r in receipts}
        assert "retrieval_dense_vectors" in ids
        assert all(r["status"] == "ROUTED_OFF_WITH_REASON" and r["reason"] for r in receipts)

    def test_set_and_reload(self, project):
        pol = RuntimePolicy(project.project_dir)
        pol.set("style.mode", "canon_mimicry")
        pol2 = RuntimePolicy(project.project_dir)
        assert pol2.style_mode == "canon_mimicry"

    def test_invalid_style_mode_falls_back_declared(self, project):
        pol = RuntimePolicy(project.project_dir)
        pol.set("style.mode", "hacker_mode")
        assert RuntimePolicy(project.project_dir).style_mode == "fanfic_voice"


# ---------------- commit hooks (INV-4) ----------------

class TestCommitGovernance:
    def test_commit_appends_event_map_and_manifest(self, project):
        res = _commit_ch(project, 1, "Nội dung chương một.")
        assert res["governance"]["event_map"] == "appended"
        assert res["governance"]["manifest"] == "regenerated"
        ev = os.path.join(project.project_dir, "timeline", "event_map.jsonl")
        rec = json.loads(open(ev, encoding="utf-8").read().strip())
        assert rec["fic_ch"] == 1
        import hashlib
        want = hashlib.sha256("Nội dung chương một.".encode()).hexdigest()
        assert rec["draft_sha256"] == want
        man = json.load(open(os.path.join(project.project_dir, "MANIFEST_SHA256.json")))
        assert "timeline/event_map.jsonl" in man["files"]

    def test_rollback_does_not_leave_governance_artifacts(self, project):
        """Fault injection giữa chừng: commit fail ⇒ không được để event_map ghi trước."""
        os.environ["FANFIC_FAULT_INJECT"] = "after_state"
        try:
            with pytest.raises(RuntimeError, match="FAULT_INJECT"):
                _commit_ch(project, 1, "Nội dung.")
        finally:
            os.environ.pop("FANFIC_FAULT_INJECT", None)
        ev = os.path.join(project.project_dir, "timeline", "event_map.jsonl")
        assert not os.path.exists(ev), "event_map không được ghi khi commit abort"


# ---------------- compliance & audit derive (INV-5, fake-USED) ----------------

class TestComplianceAudit:
    def test_fake_used_detected(self):
        rep = ComplianceReport(1)
        rep.set_status(SubsystemStatus("canon_store_rag", "USED"))  # không evidence
        problems = rep.validate_complete()
        assert any("fake-USED" in p or "evidence hash" in p for p in problems)

    def test_missing_subsystem_status_detected(self):
        rep = ComplianceReport(1)
        rep.set_status(SubsystemStatus("canon_store_rag", "USED", evidence_hash="abc123"))
        problems = rep.validate_complete()
        assert sum(1 for p in problems if "Thiếu status" in p) >= len(SUBSYSTEMS) - 1

    def test_derive_chapters_from_chain(self, project):
        """Review F-04: audit --all phải derive, không hard-code. Commit 40 chương giả."""
        for ch in range(1, 41):
            _commit_ch(project, ch, f"Nội dung {ch}.")
        nums = derive_chapter_numbers(project.project_dir)
        assert len(nums) == 40 and nums[0] == 1 and nums[-1] == 40

    def test_derive_includes_compliance_only_chapters(self, project):
        d = os.path.join(project.project_dir, "compliance")
        os.makedirs(d, exist_ok=True)
        rep = ComplianceReport(99)
        rep.save(project.project_dir)
        nums = derive_chapter_numbers(project.project_dir)
        assert 99 in nums
