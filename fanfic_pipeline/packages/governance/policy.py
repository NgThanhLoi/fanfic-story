"""
Governance P0 — Runtime policy: cấu hình layer tùy chọn per-project.

INV-3 (không silent fallback): layer tùy chọn bị tắt phải xuất hiện trong mọi
compliance report với status ROUTED_OFF_WITH_REASON. Báo USED khi thực chất
fallback là lỗi production.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_POLICY: Dict[str, Any] = {
    "version": 1,
    "style": {
        # "fanfic_voice" | "canon_mimicry" — xem spec §4.4
        "mode": "fanfic_voice",
        # Ngưỡng fidelity tối thiểu khi mode=canon_mimicry (0-100)
        "canon_min_fidelity": 90,
    },
    "retrieval": {
        # Layer tùy chọn: tắt ⇒ mọi receipt phải ghi ROUTED_OFF_WITH_REASON
        "dense_vectors": {"enabled": False, "reason": "not_configured"},
        "reranker": {"enabled": False, "reason": "not_configured"},
        # Bắt buộc theo INV-3: BM25/FTS không dấu luôn on
        "bm25_fts": {"enabled": True},
    },
    "gates": {
        "premise_validation": True,
        "readiness": True,
        "survival_floor": True,
    },
}

VALID_STYLE_MODES = ("fanfic_voice", "canon_mimicry")
# Status hợp lệ khi kê khai một subsystem trong compliance report (spec §1 registry)
SUBSYSTEM_STATUSES = ("USED", "ROUTED_OFF_WITH_REASON", "N/A_WITH_REASON", "BLOCK")


class RuntimePolicy:
    """Đọc/ghi runtime_policy.json của project; merge an toàn với DEFAULT_POLICY."""

    def __init__(self, project_dir: str):
        self.path = os.path.join(project_dir, "runtime_policy.json")
        self._policy: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        merged = json.loads(json.dumps(DEFAULT_POLICY))  # deep copy
        if os.path.exists(self.path):
            try:
                user = json.loads(Path(self.path).read_text(encoding="utf-8"))
                for section, values in (user or {}).items():
                    if isinstance(values, dict) and isinstance(merged.get(section), dict):
                        merged[section].update(values)
                    else:
                        merged[section] = values
            except Exception:
                pass  # policy hỏng ⇒ dùng default (fail-open cho config, fail-closed ở gate)
        return merged

    def save(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.path).write_text(
            json.dumps(self._policy, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @property
    def raw(self) -> Dict[str, Any]:
        return self._policy

    # ---- style ----
    @property
    def style_mode(self) -> str:
        mode = self._policy["style"]["mode"]
        return mode if mode in VALID_STYLE_MODES else "fanfic_voice"

    @property
    def canon_min_fidelity(self) -> float:
        try:
            v = float(self._policy["style"]["canon_min_fidelity"])
        except Exception:
            v = DEFAULT_POLICY["style"]["canon_min_fidelity"]
        return min(100.0, max(0.0, v))

    # ---- optional layers ----
    def optional_layers(self) -> List[str]:
        out = []
        r = self._policy["retrieval"]
        for name in ("dense_vectors", "reranker"):
            if not r[name]["enabled"]:
                out.append(name)
        return out

    def routed_off_receipts(self) -> List[Dict[str, str]]:
        """Receipt cho mọi layer đang tắt — cấm silent fallback (INV-3)."""
        out = []
        for name in self.optional_layers():
            spec = self._policy["retrieval"][name]
            out.append({
                "subsystem": f"retrieval_{name}",
                "status": "ROUTED_OFF_WITH_REASON",
                "reason": str(spec.get("reason", "user_disabled")),
            })
        return out

    def set(self, dotted_key: str, value: Any) -> None:
        node = self._policy
        parts = dotted_key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = value
        self.save()
