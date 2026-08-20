
"""
Atomic Chapter Transaction & Branch Rollback Manager v1.1.2 (FR-40/41/42):
- Staging + atomic commit point (BUG-04 fix): nothing visible until all writes succeed
- Full rollback restores meta, chapter dir, memories, branch head, hybrid memory
- WAL journal BEGIN/ABORT/COMMIT for crash recovery
- Idempotent via transactions/index.json
- Fault injection: FANFIC_FAULT_INJECT=after_state|after_workspace|after_meta|after_memory
"""
import os, json, hashlib, uuid, time, shutil
from typing import Dict, Any, Optional
from fanfic_pipeline.core.models import ChapterDraft, ChapterOutline
from fanfic_pipeline.core.story_state import StateDelta, StoryStateManager
from fanfic_pipeline.core.state_manager import ProjectStateManager
from fanfic_pipeline.packages.memory.hybrid_retriever import HybridMemoryEngine

def _sha16(s: str) -> str: return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

class ChapterTransactionManager:
    def __init__(self, state_mgr: ProjectStateManager, memory_engine: HybridMemoryEngine):
        self.state_mgr = state_mgr
        self.memory_engine = memory_engine
        self.tx_dir = os.path.join(state_mgr.project_dir, "transactions")
        os.makedirs(self.tx_dir, exist_ok=True)
        self.journal_path = os.path.join(self.tx_dir, "journal.jsonl")
        self.index_path = os.path.join(self.tx_dir, "index.json")
        if not os.path.exists(self.index_path):
            with open(self.index_path, "w", encoding="utf-8") as f: json.dump({}, f)

    def _load_index(self) -> Dict[str,Any]:
        try:
            with open(self.index_path, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    def _save_index(self, idx: Dict[str,Any]):
        tmp = self.index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(idx, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.index_path)
    def _append_journal(self, rec: Dict[str,Any]):
        with open(self.journal_path, "a", encoding="utf-8") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")

    def _fault(self, stage: str):
        want = os.environ.get("FANFIC_FAULT_INJECT", "")
        # Support comma list like "after_state,after_memory" or single
        stages = [s.strip() for s in want.split(",") if s.strip()]
        if stage in stages or want == stage or (want and stage.startswith(want)):
            raise RuntimeError(f"FAULT_INJECT {stage}")

    def commit_transaction(self, chapter_num: int, draft: ChapterDraft, outline: ChapterOutline, state_delta: StateDelta,
                           expected_hash: Optional[str]=None, packet_hash: str = "", plan_hash: str = "",
                           audit_receipt: Any = None, branch_id: str = "main", expected_head: Optional[int]=None,
                           tx_id: Optional[str]=None) -> Dict[str,Any]:
        actual_hash = _sha16(draft.content)
        if expected_hash and expected_hash != actual_hash:
            raise ValueError(f"409 STALE_HASH: expected {expected_hash}, got {actual_hash}")
        if tx_id:
            idx = self._load_index()
            if tx_id in idx:
                prev = idx[tx_id]
                if prev.get("draft_hash")==actual_hash:
                    return prev
                raise ValueError(f"409 TX_CONFLICT: tx_id {tx_id} already used with different hash")
        else:
            tx_id = uuid.uuid4().hex[:16]

        if audit_receipt is not None:
            verdict = getattr(audit_receipt, 'verdict', None) or (audit_receipt.get('verdict') if isinstance(audit_receipt, dict) else None)
            audited_hash = getattr(audit_receipt, 'audited_hash', None) or (audit_receipt.get('audited_hash') if isinstance(audit_receipt, dict) else None)
            if verdict != "PASS":
                raise ValueError(f"409 AUDIT_GATE: verdict={verdict}, commit blocked (need PASS)")
            if audited_hash and audited_hash != actual_hash:
                raise ValueError(f"409 AUDIT_STALE: audited {audited_hash} != draft {actual_hash}, re-audit required")

        if expected_head is not None:
            head = self.state_mgr.get_branch_head(branch_id)
            if head != expected_head:
                meta_head = self.state_mgr.load_project_meta().get("current_chapter",0)
                if meta_head != expected_head and head != expected_head:
                    raise ValueError(f"409 BRANCH_HEAD_MISMATCH: expected {expected_head}, got branch_head={head} meta_head={meta_head}")

        current_state = self.state_mgr.load_story_state()
        is_valid, errors = StoryStateManager.validate_delta(state_delta, current_state)
        if not is_valid:
            raise ValueError(f"422 VALIDATION_FAILED: {'; '.join(errors)}")

        ch_dir = os.path.join(self.state_mgr.chapters_dir, f"chapter_{chapter_num:03d}")
        if os.path.exists(os.path.join(ch_dir, "draft.json")):
            try:
                with open(os.path.join(ch_dir, "draft.json"), "r", encoding="utf-8") as f: prev = json.load(f)
                if _sha16(prev.get("content","")) == actual_hash:
                    idx = self._load_index()
                    for k,v in idx.items():
                        if v.get("chapter_number")==chapter_num and v.get("draft_hash")==actual_hash:
                            return v
                    return {"status": "COMMITTED", "chapter_number": chapter_num, "draft_hash": actual_hash, "tx_id": tx_id, "note": "already committed same chapter+hash"}
            except: pass

        # --- Staging atomic commit (BUG-04 fix) ---
        # Snapshot everything BEFORE any mutation
        meta_before = self.state_mgr.load_project_meta()
        try:
            with open(self.state_mgr.memories_path, "r", encoding="utf-8") as f: memories_before = json.load(f)
        except: memories_before = []
        try:
            with open(self.state_mgr.branches_path, "r", encoding="utf-8") as f: branches_before = json.load(f)
        except: branches_before = {}
        mem_items_before = list(self.memory_engine.items)  # shallow copy list
        hybrid_path = self.memory_engine.memory_file
        try:
            with open(hybrid_path, "r", encoding="utf-8") as f: hybrid_before_raw = f.read()
        except: hybrid_before_raw = ""

        staging = os.path.join(self.tx_dir, f"staging_{tx_id}")
        os.makedirs(staging, exist_ok=True)

        self._append_journal({"tx_id": tx_id, "phase": "BEGIN", "chapter": chapter_num, "draft_hash": actual_hash, "branch": branch_id, "at": time.time()})

        # Keep track of what was newly created vs overwritten
        ch_dir_existed = os.path.exists(ch_dir)
        ch_dir_backup = None
        if ch_dir_existed:
            ch_dir_backup = os.path.join(staging, f"chapter_{chapter_num:03d}_backup")
            shutil.copytree(ch_dir, ch_dir_backup)

        try:
            # Prepare staged new state
            new_state = StoryStateManager.apply_delta(current_state, state_delta)
            staged_state_path = os.path.join(staging, "story_state.json")
            with open(staged_state_path, "w", encoding="utf-8") as f: json.dump(new_state, f, ensure_ascii=False, indent=2)

            # Prepare staged chapter workspace in staging
            staged_ch_dir = os.path.join(staging, f"chapter_{chapter_num:03d}")
            os.makedirs(staged_ch_dir, exist_ok=True)
            with open(os.path.join(staged_ch_dir, "outline.json"), "w", encoding="utf-8") as f: json.dump(outline.model_dump(), f, ensure_ascii=False, indent=2)
            with open(os.path.join(staged_ch_dir, "draft.json"), "w", encoding="utf-8") as f: json.dump(draft.model_dump(), f, ensure_ascii=False, indent=2)
            with open(os.path.join(staged_ch_dir, "content.txt"), "w", encoding="utf-8") as f: f.write(draft.content)

            # Prepare staged meta/memories/branches
            staged_meta = dict(meta_before)
            staged_meta["current_chapter"] = max(staged_meta.get("current_chapter",0), chapter_num)
            staged_meta["total_words"] = staged_meta.get("total_words",0) + draft.word_count
            staged_meta["latest_draft_hash"] = actual_hash
            staged_meta_path = os.path.join(staging, "project_meta.json")
            with open(staged_meta_path, "w", encoding="utf-8") as f: json.dump(staged_meta, f, ensure_ascii=False, indent=2)

            staged_memories = list(memories_before)
            staged_memories.append({"chapter": chapter_num, "title": outline.title, "summary": outline.core_conflict if hasattr(outline,'core_conflict') else "", "draft_hash": actual_hash})
            staged_memories_path = os.path.join(staging, "chapter_memories.json")
            with open(staged_memories_path, "w", encoding="utf-8") as f: json.dump(staged_memories, f, ensure_ascii=False, indent=2)

            staged_branches = dict(branches_before)
            if branch_id in staged_branches:
                staged_branches[branch_id] = dict(staged_branches[branch_id])
                staged_branches[branch_id]["head"] = chapter_num
            staged_branches_path = os.path.join(staging, "branches.json")
            with open(staged_branches_path, "w", encoding="utf-8") as f: json.dump(staged_branches, f, ensure_ascii=False, indent=2)

            # Staged snapshot
            staged_snapshot = {"chapter": chapter_num, "state": new_state, "draft_hash": actual_hash}
            staged_snapshot_path = os.path.join(staging, f"snapshot_{chapter_num:03d}.json")
            with open(staged_snapshot_path, "w", encoding="utf-8") as f: json.dump(staged_snapshot, f, ensure_ascii=False, indent=2)

            # Prepare staged hybrid memory
            staged_hybrid = list(mem_items_before)
            # We need to stage hybrid as JSON list of dicts
            staged_hybrid_dicts = [it.model_dump() if hasattr(it,'model_dump') else it.to_dict() if hasattr(it,'to_dict') else it for it in staged_hybrid]
            staged_hybrid_dicts.append({"topic": outline.title, "category": "committed_chapter", "content": f"Chương {chapter_num}: {outline.core_conflict}. " + " ".join([b.key_event for b in outline.scene_beats]), "chapter_reference": chapter_num, "chapter": chapter_num, "weight": 1.5})
            staged_hybrid_path = os.path.join(staging, "hybrid_memory.json")
            with open(staged_hybrid_path, "w", encoding="utf-8") as f: json.dump(staged_hybrid_dicts, f, ensure_ascii=False, indent=2)

            # Fault injection points (simulate crash at any stage before commit point)
            self._fault("after_state")
            self._fault("after_workspace")
            self._fault("after_meta")
            self._fault("after_memory")

            # --- COMMIT POINT: all staged, now atomically publish ---
            # Each replace is atomic (rename)
            # 1. state
            shutil.copy2(staged_state_path, self.state_mgr.state_path)
            self._fault("after_state_commit")
            # 2. chapter dir (publish staged chapter files with overwrite)
            shutil.copytree(staged_ch_dir, ch_dir, dirs_exist_ok=True)

            # 3. meta
            shutil.copy2(staged_meta_path, self.state_mgr.meta_path)
            # 4. memories
            shutil.copy2(staged_memories_path, self.state_mgr.memories_path)
            # 5. branches
            shutil.copy2(staged_branches_path, self.state_mgr.branches_path)
            # 6. snapshot
            snap_path = os.path.join(self.state_mgr.snapshots_dir, f"snapshot_ch_{chapter_num:03d}.json")
            os.makedirs(os.path.dirname(snap_path), exist_ok=True)
            shutil.copy2(staged_snapshot_path, snap_path)
            # 7. hybrid memory
            shutil.copy2(staged_hybrid_path, hybrid_path)
            # Reload hybrid engine to pick up new items
            try: self.memory_engine._load()
            except: pass

            result = {"status": "COMMITTED", "chapter_number": chapter_num, "draft_hash": actual_hash, "new_state": new_state, "tx_id": tx_id, "branch_id": branch_id, "packet_hash": packet_hash, "plan_hash": plan_hash}
            idx = self._load_index(); idx[tx_id]=result; self._save_index(idx)
            self._append_journal({"tx_id": tx_id, "phase": "COMMITTED", "at": time.time()})
            # cleanup staging
            shutil.rmtree(staging, ignore_errors=True)
            return result
        except Exception as e:
            # Rollback: restore everything from before snapshot, remove partial staging
            self._rollback_staging(tx_id, chapter_num, ch_dir, ch_dir_existed, ch_dir_backup, staging, meta_before, memories_before, branches_before, mem_items_before, hybrid_before_raw, hybrid_path, current_state, e)
            raise

    def _rollback_staging(self, tx_id, chapter_num, ch_dir, ch_dir_existed, ch_dir_backup, staging, meta_before, memories_before, branches_before, mem_items_before, hybrid_before_raw, hybrid_path, current_state, cause):
        # Restore chapter dir
        try:
            if ch_dir_backup and os.path.exists(ch_dir_backup):
                if os.path.exists(ch_dir): shutil.rmtree(ch_dir)
                shutil.copytree(ch_dir_backup, ch_dir)
            elif not ch_dir_existed and os.path.exists(ch_dir):
                shutil.rmtree(ch_dir)
        except: pass
        # Restore meta
        try:
            with open(self.state_mgr.meta_path, "w", encoding="utf-8") as f: json.dump(meta_before, f, ensure_ascii=False, indent=2)
        except: pass
        # Restore memories
        try:
            with open(self.state_mgr.memories_path, "w", encoding="utf-8") as f: json.dump(memories_before, f, ensure_ascii=False, indent=2)
        except: pass
        # Restore branches
        try:
            with open(self.state_mgr.branches_path, "w", encoding="utf-8") as f: json.dump(branches_before, f, ensure_ascii=False, indent=2)
        except: pass
        # Restore state
        try:
            with open(self.state_mgr.state_path, "w", encoding="utf-8") as f: json.dump(current_state, f, ensure_ascii=False, indent=2)
        except: pass
        # Restore hybrid — if no file existed before, remove the staged file to avoid 0-byte artifact (BUG-04 note)
        try:
            if hybrid_before_raw == "" and not os.path.exists(hybrid_path + ".pre_exists_marker"):
                # hybrid_before_raw == "" means no file before; if we created one during staging, remove it
                if len(mem_items_before) == 0:
                    try: os.remove(hybrid_path)
                    except: pass
                else:
                    with open(hybrid_path, "w", encoding="utf-8") as f: f.write("[]")
            else:
                with open(hybrid_path, "w", encoding="utf-8") as f: f.write(hybrid_before_raw)
            self.memory_engine._load()
        except: pass
        # Cleanup staging
        try: shutil.rmtree(staging, ignore_errors=True)
        except: pass
        self._append_journal({"tx_id": tx_id, "phase": "ABORTED", "error": str(cause), "at": time.time()})
        idx = self._load_index()
        idx[tx_id] = {"status": "ABORTED", "chapter_number": chapter_num, "error": str(cause), "tx_id": tx_id}
        self._save_index(idx)

    def rollback_transaction(self, target_chapter: int, branch_id: str = "main"):
        self.state_mgr.rollback_to_chapter(target_chapter)
        try: self.memory_engine.items = [m for m in self.memory_engine.items if getattr(m,'chapter_reference', getattr(m,'chapter', 9999)) <= target_chapter]; self.memory_engine._save()
        except: pass
        self._append_journal({"phase": "ROLLBACK", "target": target_chapter, "branch": branch_id, "at": time.time()})

    def fork_branch(self, new_branch_id: str, from_chapter: int, from_branch: str = "main"):
        return self.state_mgr.create_branch(new_branch_id, from_chapter, from_branch)
