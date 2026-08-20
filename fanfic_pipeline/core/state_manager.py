
"""
State Manager v1.1 — Branch-aware, atomic writes (FR-42 + FR-40):
- branch_id on all authority objects
- _atomic_write helper (temp + rename)
- get_branch_head / create_branch / list_branches
- Backward compat: defaults to branch main
"""
import os, json, hashlib, shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from fanfic_pipeline.core.models import PointOfDivergence, CharacterVoice, RelationshipState, ChapterOutline, ChapterDraft, OOCCriticResult

DEFAULT_STORAGE_ROOT = Path(__file__).resolve().parents[1] / "storage" / "projects"

def _atomic_write(path: str, data: Any):
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

class ProjectStateManager:
    def __init__(self, project_id: str, base_dir: Optional[str] = None, branch_id: str = "main"):
        self.project_id = project_id
        self.branch_id = branch_id
        storage_root = base_dir or os.environ.get("FANFIC_STORAGE_DIR") or str(DEFAULT_STORAGE_ROOT)
        self.project_dir = os.path.join(storage_root, project_id)
        self.chapters_dir = os.path.join(self.project_dir, "chapters")
        self.snapshots_dir = os.path.join(self.project_dir, "snapshots")
        self.meta_path = os.path.join(self.project_dir, "project_meta.json")
        self.pod_path = os.path.join(self.project_dir, "pod_ledger.json")
        self.voices_path = os.path.join(self.project_dir, "character_voices.json")
        self.relationship_path = os.path.join(self.project_dir, "relationship_matrix.json")
        self.state_path = os.path.join(self.project_dir, "story_state.json")
        self.memories_path = os.path.join(self.project_dir, "chapter_memories.json")
        self.branches_path = os.path.join(self.project_dir, "branches.json")
        self._ensure_dirs()
        self._init_memory_store()

    def _ensure_dirs(self):
        os.makedirs(self.project_dir, exist_ok=True)
        os.makedirs(self.chapters_dir, exist_ok=True)
        os.makedirs(self.snapshots_dir, exist_ok=True)

    def _init_memory_store(self):
        if not os.path.exists(self.memories_path):
            _atomic_write(self.memories_path, [])

    def init_project(self, title: str, fandom: str, pod: PointOfDivergence, voices: Dict[str, CharacterVoice], relationships: List[RelationshipState], execution_mode: str = "HUMAN_IN_THE_LOOP"):
        meta = {"project_id": self.project_id, "branch_id": "main", "branches": ["main"], "title": title, "fandom": fandom, "execution_mode": execution_mode, "current_chapter": 0, "total_words": 0, "latest_draft_hash": ""}
        _atomic_write(self.meta_path, meta)
        with open(self.pod_path, "w", encoding="utf-8") as f: json.dump(pod.model_dump(), f, ensure_ascii=False, indent=2)
        with open(self.voices_path, "w", encoding="utf-8") as f: json.dump({k: v.model_dump() for k,v in voices.items()}, f, ensure_ascii=False, indent=2)
        with open(self.relationship_path, "w", encoding="utf-8") as f: json.dump([r.model_dump() for r in relationships], f, ensure_ascii=False, indent=2)
        initial_state = {"current_location": "Không gian Lục Đạo Luân Hồi", "active_characters": ["Mạnh Kỳ","Giang Chỉ Vi","Tề Chính Ngôn","Nguyễn Ngọc Thư"], "team_thien_cong": {"Mạnh Kỳ":100,"Giang Chỉ Vi":120,"Tề Chính Ngôn":90,"Nguyễn Ngọc Thư":110}, "unresolved_hooks": ["Thân phận thực sự của Lục Đạo","Bí ẩn sau lần trọng sinh của Mạnh Kỳ"], "timeline_stage": "Nhiệm vụ Luân Hồi Tân Thủ - Cảnh Khai Khiếu sơ kỳ", "branch_id": "main"}
        _atomic_write(self.state_path, initial_state)
        # branches file
        _atomic_write(self.branches_path, {"main": {"from_chapter": 0, "from_branch": None, "created_at": "", "head": 0}})

    def load_project_meta(self) -> Dict[str, Any]:
        if not os.path.exists(self.meta_path): return {}
        with open(self.meta_path, "r", encoding="utf-8") as f: return json.load(f)
    def update_project_meta(self, updates: Dict[str, Any]):
        meta = self.load_project_meta(); meta.update(updates); _atomic_write(self.meta_path, meta)
    def load_pod(self) -> PointOfDivergence:
        with open(self.pod_path, "r", encoding="utf-8") as f: return PointOfDivergence(**json.load(f))
    def save_pod(self, pod: PointOfDivergence):
        _atomic_write(self.pod_path, pod.model_dump())
    def load_voices(self) -> Dict[str, CharacterVoice]:

        with open(self.voices_path, "r", encoding="utf-8") as f: data=json.load(f); return {k: CharacterVoice(**v) for k,v in data.items()}
    def load_relationships(self) -> List[RelationshipState]:
        with open(self.relationship_path, "r", encoding="utf-8") as f: data=json.load(f); return [RelationshipState(**r) for r in data]
    def load_story_state(self) -> Dict[str, Any]:
        with open(self.state_path, "r", encoding="utf-8") as f: return json.load(f)
    def update_story_state(self, updates: Dict[str, Any]):
        state = self.load_story_state(); state.update(updates); _atomic_write(self.state_path, state)
    def calculate_draft_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    def save_chapter_workspace(self, chapter_num: int, outline: ChapterOutline, draft: ChapterDraft):
        ch_dir = os.path.join(self.chapters_dir, f"chapter_{chapter_num:03d}")
        os.makedirs(ch_dir, exist_ok=True)
        _atomic_write(os.path.join(ch_dir, "outline.json"), outline.model_dump())
        _atomic_write(os.path.join(ch_dir, "draft.json"), draft.model_dump())
        # also write content.txt atomically
        ct = os.path.join(ch_dir, "content.txt")
        tmp = ct + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: f.write(draft.content)
        os.replace(tmp, ct)

    def commit_chapter(self, chapter_num: int, draft: ChapterDraft, outline: ChapterOutline, expected_hash: Optional[str]=None):
        # legacy path — used by old daemon, now delegates to verify hash then update meta
        if expected_hash and expected_hash != self.calculate_draft_hash(draft.content):
            raise ValueError(f"Stale hash: expected {expected_hash}")
        meta = self.load_project_meta()
        meta["current_chapter"] = max(meta.get("current_chapter",0), chapter_num)
        meta["total_words"] = meta.get("total_words",0) + draft.word_count
        meta["latest_draft_hash"] = self.calculate_draft_hash(draft.content)
        _atomic_write(self.meta_path, meta)
        # memories
        try:
            with open(self.memories_path, "r", encoding="utf-8") as f: mems=json.load(f)
        except: mems=[]
        mems.append({"chapter": chapter_num, "title": outline.title, "summary": outline.core_conflict if hasattr(outline,'core_conflict') else "", "draft_hash": meta["latest_draft_hash"]})
        _atomic_write(self.memories_path, mems)
        # snapshot
        snap_path = os.path.join(self.snapshots_dir, f"snapshot_ch_{chapter_num:03d}.json")
        _atomic_write(snap_path, {"chapter": chapter_num, "state": self.load_story_state(), "draft_hash": meta["latest_draft_hash"]})

    def get_recent_summaries(self, limit: int = 5, limits: Optional[int] = None) -> List[Dict[str,Any]]:
        max_items = limits if limits is not None else limit
        try:
            with open(self.memories_path, "r", encoding="utf-8") as f: mems=json.load(f)
            return mems[-max_items:]
        except: return []


    # --- Branch support (FR-42) ---
    def get_branch_head(self, branch_id: str = "main") -> int:
        try:
            with open(self.branches_path, "r", encoding="utf-8") as f: br=json.load(f)
            return br.get(branch_id, {}).get("head", 0)
        except: return self.load_project_meta().get("current_chapter",0)
    def list_branches(self) -> List[str]:
        try:
            with open(self.branches_path, "r", encoding="utf-8") as f: return list(json.load(f).keys())
        except: return ["main"]
    def create_branch(self, new_branch_id: str, from_chapter: int, from_branch: str = "main"):
        try:
            with open(self.branches_path, "r", encoding="utf-8") as f: br=json.load(f)
        except: br={"main": {"from_chapter":0,"from_branch":None,"head": self.load_project_meta().get("current_chapter",0)}}
        if new_branch_id in br: raise ValueError(f"Branch {new_branch_id} already exists")
        br[new_branch_id] = {"from_chapter": from_chapter, "from_branch": from_branch, "head": from_chapter}
        _atomic_write(self.branches_path, br)
        # also record in meta branches list
        meta=self.load_project_meta(); blist=meta.get("branches", ["main"])
        if new_branch_id not in blist: blist.append(new_branch_id)
        meta["branches"]=blist; _atomic_write(self.meta_path, meta)
        return br[new_branch_id]
    def rollback_to_chapter(self, target_chapter: int):
        meta=self.load_project_meta()
        # Snapshot is source of truth
        snap = os.path.join(self.snapshots_dir, f"snapshot_ch_{target_chapter:03d}.json")
        snap_data = None
        if os.path.exists(snap):
            try:
                with open(snap,"r",encoding="utf-8") as f: snap_data=json.load(f)
            except: pass
        # Recompute total_words from surviving chapter dirs
        total_words = 0
        if target_chapter == 0:
            meta["current_chapter"] = 0
            meta["total_words"] = 0
            meta["latest_draft_hash"] = ""
        else:
            meta["current_chapter"] = target_chapter
            if snap_data and "draft_hash" in snap_data:
                meta["latest_draft_hash"] = snap_data["draft_hash"]
            else:
                # fallback: hash from chapter draft
                try:
                    with open(os.path.join(self.chapters_dir, f"chapter_{target_chapter:03d}", "draft.json"), "r", encoding="utf-8") as f:
                        d=json.load(f)
                        meta["latest_draft_hash"] = self.calculate_draft_hash(d.get("content",""))
                except: pass
            # Recompute total_words
            for ch in range(1, target_chapter+1):
                draft_path = os.path.join(self.chapters_dir, f"chapter_{ch:03d}", "draft.json")
                if os.path.exists(draft_path):
                    try:
                        with open(draft_path, "r", encoding="utf-8") as f: d=json.load(f)
                        total_words += d.get("word_count", 0)
                    except: pass
            meta["total_words"] = total_words
        _atomic_write(self.meta_path, meta)
        # prune memories
        try:
            with open(self.memories_path,"r",encoding="utf-8") as f: mems=json.load(f)
            mems=[m for m in mems if m.get("chapter",0) <= target_chapter]
            _atomic_write(self.memories_path, mems)
        except: pass
        # restore state from snapshot
        if snap_data and "state" in snap_data:
            try: _atomic_write(self.state_path, snap_data["state"])
            except: pass
        # update branch head
        try:
            with open(self.branches_path, "r", encoding="utf-8") as f: br=json.load(f)
            for bid in list(br.keys()):
                if br[bid].get("head", 0) > target_chapter:
                    br[bid]["head"] = target_chapter
            _atomic_write(self.branches_path, br)
        except: pass
        # move future chapter dirs to trash (keep for undo)
        trash = os.path.join(self.project_dir, "trash")
        os.makedirs(trash, exist_ok=True)
        for ch in range(target_chapter+1, 9999):
            ch_dir = os.path.join(self.chapters_dir, f"chapter_{ch:03d}")
            if not os.path.exists(ch_dir): 
                # stop after first gap only if we already removed some; otherwise keep scanning a bit
                if ch > target_chapter+5: break
                continue
            dest = os.path.join(trash, f"chapter_{ch:03d}")
            if os.path.exists(dest): shutil.rmtree(dest)
            shutil.move(ch_dir, dest)
        # also remove future snapshots
        for ch in range(target_chapter+1, 9999):
            sp = os.path.join(self.snapshots_dir, f"snapshot_ch_{ch:03d}.json")
            if not os.path.exists(sp):
                if ch > target_chapter+5: break
                continue
            dest = os.path.join(trash, f"snapshot_ch_{ch:03d}.json")
            try: shutil.move(sp, dest)
            except: 
                try: os.remove(sp)
                except: pass
