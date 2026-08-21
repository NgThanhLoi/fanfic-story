"""
P4 E2E — Provenance chain + smoke dry-run toàn pipeline (spec §6 P4).

- INV-4: draft SHA ↔ event_map ↔ manifest khớp sau commit; doctor bắt stale
- Smoke không-API-key: init → readiness → write-next --force-auto → doctor → audit
- Reference read-only guard: runtime không import từ docs/references/
- Style mode switch qua CLI policy phản ánh vào runtime policy file
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLI = [sys.executable, os.path.join(REPO, "fanfic_pipeline", "fanfic_cli.py")]


@pytest.fixture()
def project_env():
    tmp = tempfile.mkdtemp(prefix="p4e2e_")
    env = dict(os.environ)
    env["FANFIC_STORAGE_DIR"] = tmp
    try:
        yield tmp, env
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(env, *args, expect_rc=0):
    p = subprocess.run(CLI + list(args), capture_output=True, text=True, env=env)
    if expect_rc == 0:
        assert p.returncode == 0, f"rc={p.returncode}\n{p.stdout[-800:]}\n{p.stderr[-300:]}"
    else:
        assert p.returncode != 0, f"expected failure\n{p.stdout[-400:]}"
    return p


class TestProvenanceChain:
    def test_full_chain_after_commit(self, project_env):
        """INV-4: draft SHA trong event_map == SHA nội dung chương; manifest khớp."""
        tmp, env = project_env
        run(env, "init", "--project", "e2e", "--title", "E2E", "--mode", "auto")
        # foundation: canon_ingested + commit 1 chương qua transaction manager trực tiếp
        sys.path.insert(0, REPO)
        from fanfic_pipeline.core.state_manager import ProjectStateManager
        from fanfic_pipeline.core.models import (PointOfDivergence, ChapterDraft,
                                                 ChapterOutline, SceneBeat)
        from fanfic_pipeline.core.story_state import StateDelta
        from fanfic_pipeline.packages.memory.hybrid_retriever import HybridMemoryEngine
        from fanfic_pipeline.core.transaction_manager import ChapterTransactionManager
        mgr = ProjectStateManager("e2e", base_dir=tmp)
        meta = mgr.load_project_meta(); meta["canon_ingested"] = True
        mgr.update_project_meta(meta)
        content = "Nội dung chương một cho e2e provenance."
        mem = HybridMemoryEngine(os.path.join(mgr.project_dir, "hybrid_memory.json"))
        tx = ChapterTransactionManager(mgr, mem)
        draft = ChapterDraft(chapter_number=1, title="C1", word_count=2,
                             content=content, summary="s")
        outline = ChapterOutline(chapter_number=1, title="C1", point_of_view="Mạnh Kỳ",
                                 core_conflict="c",
                                 scene_beats=[SceneBeat(beat_number=1, scene_type="action",
                                                        characters_present=["Mạnh Kỳ"],
                                                        a_plot_goal="A", b_plot_goal="B",
                                                        key_event="K", tension_element="T")])
        res = tx.commit_transaction(1, draft, outline,
                                    state_delta=StateDelta(chapter_number=1),
                                    expected_hash=mgr.calculate_draft_hash(content))
        assert res["governance"]["event_map"] == "appended"
        # draft_sha256 trong event_map == sha256(content)
        ev_path = os.path.join(mgr.project_dir, "timeline", "event_map.jsonl")
        rec = json.loads(open(ev_path, encoding="utf-8").read().strip())
        want = hashlib.sha256(content.encode()).hexdigest()
        assert rec["draft_sha256"] == want
        # compliance report tồn tại với subsystem statuses đầy đủ
        comp_p = os.path.join(mgr.project_dir, "compliance", "ch0001_compliance.json")
        comp = json.load(open(comp_p, encoding="utf-8"))
        declared = {s["subsystem"] for s in comp["subsystems"]}
        fake_used = [s for s in comp["subsystems"]
                     if s["status"] == "USED" and not s.get("evidence_sha256")]
        assert not fake_used
        assert len(declared) >= 13
        # doctor PASS trên chain sạch
        run(env, "doctor", "--project", "e2e")

    def test_doctor_detects_manifest_stale(self, project_env):
        """INV-4: sửa tay story_state sau commit ⇒ doctor phải báo manifest stale."""
        tmp, env = project_env
        run(env, "init", "--project", "e2e", "--title", "E2E", "--mode", "auto")
        sys.path.insert(0, REPO)
        from fanfic_pipeline.core.state_manager import ProjectStateManager
        from fanfic_pipeline.core.models import (PointOfDivergence, ChapterDraft,
                                                 ChapterOutline, SceneBeat)
        from fanfic_pipeline.core.story_state import StateDelta
        from fanfic_pipeline.packages.memory.hybrid_retriever import HybridMemoryEngine
        from fanfic_pipeline.core.transaction_manager import ChapterTransactionManager
        mgr = ProjectStateManager("e2e", base_dir=tmp)
        mem = HybridMemoryEngine(os.path.join(mgr.project_dir, "hybrid_memory.json"))
        tx = ChapterTransactionManager(mgr, mem)
        draft = ChapterDraft(chapter_number=1, title="C1", word_count=2,
                             content="Nội dung.", summary="s")
        outline = ChapterOutline(chapter_number=1, title="C1", point_of_view="Mạnh Kỳ",
                                 core_conflict="c",
                                 scene_beats=[SceneBeat(beat_number=1, scene_type="action",
                                                        characters_present=["Mạnh Kỳ"],
                                                        a_plot_goal="A", b_plot_goal="B",
                                                        key_event="K", tension_element="T")])
        tx.commit_transaction(1, draft, outline, state_delta=StateDelta(chapter_number=1))
        # tamper: sửa story_state ngoài pipeline
        state = json.load(open(mgr.state_path, encoding="utf-8"))
        state["tampered_field"] = True
        with open(mgr.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        p = run(env, "doctor", "--project", "e2e", expect_rc=1)
        assert "stale" in p.stdout.lower() or "mismatch" in p.stdout.lower()


class TestSmokeDryRun:
    def test_full_pipeline_no_api_key(self, project_env):
        """Smoke dry-run: init → readiness BLOCK → fix foundation → READY →
        write-next --force-auto (demo mode) → doctor → audit --all."""
        tmp, env = project_env
        env.pop("CLIPROXY_KEY", None)
        env.pop("OPENAI_API_KEY", None)
        run(env, "init", "--project", "smoke", "--title", "S", "--mode", "auto")
        # readiness BLOCK vì chưa ingest canon
        p = run(env, "readiness", "--project", "smoke", "--chapter", "1", expect_rc=1)
        assert "canon_ingested" in p.stdout or "BLOCK" in p.stdout
        # fix foundation + premise artifacts hợp lệ
        sys.path.insert(0, REPO)
        from fanfic_pipeline.core.state_manager import ProjectStateManager
        mgr = ProjectStateManager("smoke", base_dir=tmp)
        meta = mgr.load_project_meta(); meta["canon_ingested"] = True
        mgr.update_project_meta(meta)
        spec = ("Chương mở đầu: Mạnh Kỳ rời Thiếu Lâm xuống núi, rèn đao ý mỗi sáng; "
                "chuẩn bị khai nhĩ khiếu theo đúng thứ tự ở chặng sau.")
        p = run(env, "readiness", "--project", "smoke", "--chapter", "1")
        assert "READY" in p.stdout
        # write-next demo mode
        run(env, "write-next", "--project", "smoke", "--force-auto")
        run(env, "doctor", "--project", "smoke")
        run(env, "audit", "--all", "--project", "smoke")

    def test_style_mode_via_policy(self, project_env):
        tmp, env = project_env
        run(env, "init", "--project", "smoke", "--title", "S", "--mode", "auto")
        run(env, "policy", "set", "--project", "smoke",
            "--key", "style.mode", "--value", "canon_mimicry")
        p = run(env, "policy", "show", "--project", "smoke")
        pol = json.loads(p.stdout)
        assert pol["style"]["mode"] == "canon_mimicry"


class TestReferenceReadOnly:
    def test_runtime_never_imports_reference(self):
        """Guard: fanfic_pipeline KHÔNG được import từ docs/references."""
        hits = []
        for root, _, files in os.walk(os.path.join(REPO, "fanfic_pipeline")):
            if "__pycache__" in root:
                continue
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                src = open(os.path.join(root, fn), encoding="utf-8").read()
                if "docs/references" in src.replace("\\", "/") and "KHÔNG BAO GIỜ" not in src:
                    hits.append(fn)
        assert not hits, f"runtime import từ reference: {hits}"
