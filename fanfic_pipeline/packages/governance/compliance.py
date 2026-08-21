"""
Governance P0 — Subsystem registry + per-chapter compliance (INV-3, INV-5).

Mọi chương phải kê khai từng registered subsystem với đúng một status:
USED | ROUTED_OFF_WITH_REASON | N/A_WITH_REASON | BLOCK.
Fake USED (không có evidence hash) bị test đối kháng bắt.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fanfic_pipeline.packages.governance.policy import SUBSYSTEM_STATUSES

# Registered subsystems của pipeline sau merge (spec §1). Mỗi entry: id, stage, mode.
SUBSYSTEMS: List[Dict[str, str]] = [
    {"id": "canon_store_rag",        "stage": "pre-draft",  "mode": "required"},
    {"id": "vi_canon_retrieval",     "stage": "pre-draft",  "mode": "required"},
    {"id": "retrieval_dense_vectors","stage": "pre-draft",  "mode": "optional_user_routed"},
    {"id": "retrieval_reranker",     "stage": "pre-draft",  "mode": "optional_user_routed"},
    {"id": "identity_coref",         "stage": "pre-draft",  "mode": "required"},
    {"id": "capability_timeline",    "stage": "pre-draft",  "mode": "required"},
    {"id": "social_web",             "stage": "pre-draft",  "mode": "required_or_na"},
    {"id": "oc_power_system",        "stage": "pre-draft",  "mode": "required_or_na"},
    {"id": "narrative_ledgers",      "stage": "pre-draft",  "mode": "required"},
    {"id": "butterfly_engine",       "stage": "post-draft", "mode": "required"},
    {"id": "style_profile",          "stage": "post-draft", "mode": "required"},
    {"id": "audit_gate",             "stage": "post-draft", "mode": "required"},
    {"id": "transaction_commit",     "stage": "commit",     "mode": "required"},
]


class SubsystemStatus:
    def __init__(self, subsystem_id: str, status: str, reason: str = "",
                 evidence_hash: str = ""):
        if status not in SUBSYSTEM_STATUSES:
            raise ValueError(f"Status '{status}' không hợp lệ; dùng {SUBSYSTEM_STATUSES}")
        self.subsystem_id = subsystem_id
        self.status = status
        self.reason = reason
        self.evidence_hash = evidence_hash  # trace/output hash của run hiện tại

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem": self.subsystem_id,
            "status": self.status,
            "reason": self.reason,
            "evidence_sha256": self.evidence_hash or None,
        }


def evidence_hash(*parts: str) -> str:
    return hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()[:16]


class ComplianceReport:
    """Report 4 nhóm Canon/Power/Pipeline/State cho một chương (chuẩn review §18)."""

    def __init__(self, chapter_number: int):
        self.chapter_number = chapter_number
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.subsystem_statuses: List[SubsystemStatus] = []
        self.sections: Dict[str, Dict[str, Any]] = {
            "canon": {}, "power": {}, "pipeline": {}, "state": {},
        }
        self.premise_receipt_hash: Optional[str] = None
        self.draft_sha256: Optional[str] = None
        self.manifest_fresh: Optional[bool] = None

    def set_status(self, s: SubsystemStatus) -> None:
        self.subsystem_statuses = [x for x in self.subsystem_statuses
                                   if x.subsystem_id != s.subsystem_id]
        self.subsystem_statuses.append(s)

    def validate_complete(self) -> List[str]:
        """INV-5/INV-3: mọi registered subsystem phải có đúng một status;
        USED phải có evidence hash; ROUTED_OFF phải có reason."""
        problems = []
        declared = {s.subsystem_id for s in self.subsystem_statuses}
        for reg in SUBSYSTEMS:
            sid = reg["id"]
            if sid not in declared:
                problems.append(f"Thiếu status cho subsystem '{sid}'")
        for s in self.subsystem_statuses:
            if s.status == "USED" and not s.evidence_hash:
                problems.append(f"'{s.subsystem_id}' khai USED nhưng không có evidence hash (fake-USED)")
            if s.status == "ROUTED_OFF_WITH_REASON" and not s.reason:
                problems.append(f"'{s.subsystem_id}' ROUTED_OFF nhưng thiếu reason")
        return problems

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "created_at": self.created_at,
            "sections": self.sections,
            "premise_receipt_hash": self.premise_receipt_hash,
            "draft_sha256": self.draft_sha256,
            "manifest_fresh": self.manifest_fresh,
            "subsystems": [s.to_dict() for s in self.subsystem_statuses],
        }

    def save(self, project_dir: str) -> str:
        d = os.path.join(project_dir, "compliance")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"ch{self.chapter_number:04d}_compliance.json")
        Path(p).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                           encoding="utf-8")
        return p


def derive_chapter_numbers(project_dir: str) -> List[int]:
    """INV-5: danh sách chương derive từ committed chain + compliance specs.
    KHÔNG hard-code range (bài học review F-04: audit --all chỉ chạy FC1-10)."""
    nums = set()
    meta_p = os.path.join(project_dir, "project_meta.json")
    if os.path.exists(meta_p):
        try:
            meta = json.loads(Path(meta_p).read_text(encoding="utf-8"))
            cur = int(meta.get("current_chapter", 0))
            nums.update(range(1, cur + 1))
        except Exception:
            pass
    comp_d = os.path.join(project_dir, "compliance")
    if os.path.isdir(comp_d):
        for fn in os.listdir(comp_d):
            m = __import__("re").match(r"ch(\d+)_compliance\.json", fn)
            if m:
                nums.add(int(m.group(1)))
    ev_d = os.path.join(project_dir, "timeline")
    ev_p = os.path.join(ev_d, "event_map.jsonl") if os.path.isdir(ev_d) else None
    if ev_p and os.path.exists(ev_p):
        for line in open(ev_p, encoding="utf-8"):
            try:
                nums.add(int(json.loads(line)["fic_ch"]))
            except Exception:
                pass
    return sorted(nums)
