"""
Governance P0 — Premise validation (INV-1).

"Pipeline enforce đúng premise sai vẫn ra chương sai" (review §2.3/§23).
Không planning artifact nào (chapter spec, outline, scene dossier) được làm
đầu vào tin cậy của readiness gate nếu chưa qua canon-validate.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fanfic_pipeline.packages.governance.topology import (
    TransitionTopology,
    TopologyViolation,
    load_default_topology,
)


class PremiseReceipt:
    """Kết quả premise-validation, hash-bind vào prewrite receipt sau này."""

    def __init__(self, ok: bool, violations: List[Dict[str, Any]],
                 artifacts: Dict[str, str], topology_path: str):
        self.ok = ok
        self.violations = violations
        self.artifacts = artifacts            # name -> sha256(nội dung artifact)
        self.topology_path = topology_path
        self.validated_at = datetime.now(timezone.utc).isoformat()

    @property
    def receipt_hash(self) -> str:
        payload = json.dumps({
            "ok": self.ok,
            "violations": self.violations,
            "artifacts": self.artifacts,
        }, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "receipt_hash": self.receipt_hash,
            "violations": self.violations,
            "artifact_hashes": self.artifacts,
            "topology": os.path.basename(self.topology_path),
            "validated_at": self.validated_at,
        }


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PremiseValidator:
    def __init__(self, topology: Optional[TransitionTopology] = None):
        self.topology = topology or load_default_topology()
        if self.topology is None:
            raise FileNotFoundError(
                "aperture_topology.json không tồn tại — premise gate fail-closed "
                "(chạy lại data import hoặc trỏ topology path đúng).")

    def validate(self, committed_opened: List[str],
                 artifacts: Optional[Dict[str, str]] = None,
                 exception_receipts: Optional[List[str]] = None) -> PremiseReceipt:
        """artifacts: {tên: nội dung text} — chapter spec / outline / scene dossier.
        Mọi artifact phải pass; một vi phạm ⇒ toàn bộ premise BLOCK."""
        artifacts = artifacts or {}
        all_violations: List[TopologyViolation] = []
        hashes: Dict[str, str] = {}
        for name, text in artifacts.items():
            hashes[name] = _sha256_text(text)
            for v in self.topology.validate_artifact(text, committed_opened, exception_receipts):
                v.detail["artifact"] = name
                all_violations.append(v)
        return PremiseReceipt(
            ok=not all_violations,
            violations=[v.to_dict() for v in all_violations],
            artifacts=hashes,
            topology_path=self.topology.path,
        )
