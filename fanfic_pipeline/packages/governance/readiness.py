"""
Governance P0 — Pre-write readiness gate (INV-1, INV-2).

"Never draft merely because the user says write/continue."
READY mới cho phép DRAFT; BLOCK phải liệt kê blockers để sửa foundation.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fanfic_pipeline.packages.governance.policy import RuntimePolicy
from fanfic_pipeline.packages.governance.premise import PremiseValidator, PremiseReceipt
from fanfic_pipeline.packages.governance.topology import (
    TransitionTopology, load_default_topology,
)


class ReadinessResult:
    def __init__(self, chapter_number: int):
        self.chapter_number = chapter_number
        self.verdict: str = "READY"          # READY | BLOCK
        self.blockers: List[Dict[str, Any]] = []
        self.checks: Dict[str, str] = {}     # check_name -> PASS|BLOCK|SKIP(reason)
        self.premise: Optional[PremiseReceipt] = None
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def block(self, check: str, message: str, detail: Optional[Dict] = None) -> None:
        self.verdict = "BLOCK"
        self.checks[check] = "BLOCK"
        self.blockers.append({"check": check, "message": message, "detail": detail or {}})

    def pass_check(self, check: str) -> None:
        self.checks[check] = "PASS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "verdict": self.verdict,
            "checks": self.checks,
            "blockers": self.blockers,
            "premise_receipt_hash": self.premise.receipt_hash if self.premise else None,
            "timestamp": self.timestamp,
        }


class ReadinessGate:
    def __init__(self, state_mgr, topology: Optional[TransitionTopology] = None):
        """state_mgr: ProjectStateManager (dùng load_project_meta / project_dir)."""
        self.mgr = state_mgr
        self.policy = RuntimePolicy(state_mgr.project_dir)
        self.topology = topology or load_default_topology()

    # ---- checks ----
    def _check_project(self, r: ReadinessResult) -> bool:
        meta = self.mgr.load_project_meta()
        if not meta:
            r.block("project_exists", f"Không tìm thấy project — chạy 'init' trước.")
            return False
        r.pass_check("project_exists")
        return True

    def _check_predecessor_chain(self, chapter_number: int, r: ReadinessResult) -> bool:
        """INV-2: predecessor phải committed; chain đọc từ event_map (single-source head)."""
        meta = self.mgr.load_project_meta()
        current = int(meta.get("current_chapter", 0))
        if chapter_number != current + 1:
            r.block("sequential_commit",
                    f"Chương yêu cầu {chapter_number} nhưng durable head là {current} "
                    f"(chỉ được viết current+1).",
                    {"requested": chapter_number, "head": current})
            return False
        ev_p = os.path.join(self.mgr.project_dir, "timeline", "event_map.jsonl")
        if current > 0:
            if not os.path.exists(ev_p):
                r.block("event_map", "timeline/event_map.jsonl thiếu dù đã có chương committed "
                                     "(chain không audit được).")
                return False
            have = set()
            for line in open(ev_p, encoding="utf-8"):
                try:
                    have.add(int(json.loads(line)["fic_ch"]))
                except Exception:
                    pass
            missing = [n for n in range(1, current + 1) if n not in have]
            if missing:
                r.block("event_map", f"event_map thiếu chương {missing[:5]} — provenance chain đứt.")
                return False
        r.pass_check("sequential_commit")
        return True

    def _check_premise(self, chapter_number: int, artifacts: Dict[str, str],
                       exception_receipts: Optional[List[str]], r: ReadinessResult) -> bool:
        if not self.policy.raw["gates"]["premise_validation"]:
            # Gate tắt trong policy vẫn phải hiện rõ (không silent)
            r.checks["premise_validation"] = "SKIP(policy off)"
            return True
        validator = PremiseValidator(topology=self.topology)
        meta = self.mgr.load_story_state() or {}
        committed_opened = list(meta.get("opened_apertures", []))
        receipt = validator.validate(committed_opened, artifacts, exception_receipts)
        r.premise = receipt
        if not receipt.ok:
            for v in receipt.violations:
                r.block("premise_validation",
                        f"[{v['kind']}] {v['message']}", v)
            return False
        r.pass_check("premise_validation")
        return True

    def _check_canon_foundation(self, r: ReadinessResult) -> bool:
        canon_dir = os.path.join(self.mgr.project_dir, "canon_store")
        has_canon = os.path.isdir(canon_dir) and any(
            f.endswith(".json") for f in os.listdir(canon_dir))
        meta = self.mgr.load_project_meta()
        ingested = bool(meta and meta.get("canon_ingested"))
        if not (has_canon or ingested):
            r.block("canon_ingested",
                    "Canon chưa ingest — RAG trống. Chạy: ingest --epub <file.epub>")
            return False
        r.pass_check("canon_ingested")
        return True

    def _check_survival_floor(self, chapter_number: int, mission_meta: Optional[Dict], r: ReadinessResult) -> None:
        """P3 sẽ mở rộng; P0 chỉ enforce khi project meta khai lethal_mission."""
        if not self.policy.raw["gates"]["survival_floor"] or not mission_meta:
            return
        if mission_meta.get("lethal_mission") and not mission_meta.get("survival_receipt_ready"):
            r.block("survival_floor",
                    "Nhiệm vụ tử địa nhưng survival-readiness receipt chưa READY "
                    "(spec §4.2: balance có sàn, không balance bằng bất lực).")

    # ---- entry ----
    def evaluate(self, chapter_number: int,
                 planning_artifacts: Optional[Dict[str, str]] = None,
                 exception_receipts: Optional[List[str]] = None,
                 mission_meta: Optional[Dict] = None) -> ReadinessResult:
        r = ReadinessResult(chapter_number)
        if not self._check_project(r):
            return r
        ok = self._check_predecessor_chain(chapter_number, r)
        ok = self._check_canon_foundation(r) and ok
        ok = self._check_premise(chapter_number, planning_artifacts or {}, exception_receipts, r) and ok
        self._check_survival_floor(chapter_number, mission_meta, r)
        return r


def save_readiness(project_dir: str, result: ReadinessResult) -> str:
    d = os.path.join(project_dir, "readiness")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"ch{result.chapter_number:04d}_readiness.json")
    Path(p).write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
                       encoding="utf-8")
    return p
