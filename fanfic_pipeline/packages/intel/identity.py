"""
P3 — Intel: identity coreference, capability timeline, arc ledger.

- identity.py (module này): canonical hóa bí danh zh↔vi theo mốc thời gian;
  resolve surfaces → canonical entity CHỈ khi canon_time >= reveal_chapter
  (spoiler-sensitive fail-closed).
- capability(): nhân vật X biết/làm được gì ở canon ch.N — time-indexed facts.
- ArcLedger: sổ phát triển nhân vật (INV-8): mọi drift tính cách/quan hệ giữa
  hai chương phải có causal receipt từ sự kiện đã commit.
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fanfic_pipeline.packages.governance.topology import normalize_vi

_DATA = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "nhat_the_chi_ton"))


def _load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


class IdentityResolver:
    def __init__(self, registry_path: Optional[str] = None):
        self.registry = _load_jsonl(registry_path or os.path.join(_DATA, "identity_registry.jsonl"))

    def surfaces_for(self, canonical_zh: str, as_of_chapter: int,
                     include_spoiler: bool = False) -> List[Dict[str, Any]]:
        """Bí danh CÓ THỂ dùng ở mốc as_of_chapter. Spoiler-sensitive surface
        chỉ lộ khi reveal_chapter <= as_of."""
        out = []
        for row in self.registry:
            if row.get("canonical_entity_zh") != canonical_zh:
                continue
            reveal = row.get("reveal_chapter", 1)
            spoiler = bool(row.get("spoiler_sensitive"))
            visible = (as_of_chapter is None or reveal <= as_of_chapter)
            if not visible and not include_spoiler:
                continue
            out.append({
                "identity_id": row["identity_id"],
                "surfaces_vi": row.get("surfaces_vi", []),
                "surfaces_zh": row.get("surfaces_zh", []),
                "relation_type": row.get("relation_type"),
                "visible": visible,
            })
        return out

    def check_prose(self, draft: str, as_of_chapter: int) -> List[Dict[str, Any]]:
        """Trả về các vi phạm: surface chưa-reveal xuất hiện trong văn.
        (Checker identity_reveal P0 đã chặn ở audit gate; hàm này cho context pack.)"""
        norm = normalize_vi(draft)
        violations = []
        for row in self.registry:
            reveal = row.get("reveal_chapter", 1)
            if as_of_chapter is not None and reveal <= as_of_chapter:
                continue
            for surface in list(row.get("surfaces_vi", [])) + list(row.get("surfaces_zh", [])):
                if surface and normalize_vi(surface) in norm:
                    violations.append({
                        "surface": surface,
                        "identity_id": row["identity_id"],
                        "reveal_chapter": reveal,
                    })
        return violations


class CapabilityTimeline:
    def __init__(self, timeline_path: Optional[str] = None):
        self.events = _load_jsonl(timeline_path or os.path.join(_DATA, "capability_timeline.jsonl"))

    def capabilities_as_of(self, entity_contains: str, as_of_chapter: int) -> List[Dict[str, Any]]:
        """Sự kiện năng lực của nhân vật tính đến canon ch.N (time-indexed)."""
        needle = entity_contains.lower()
        out = []
        for ev in self.events:
            if needle not in str(ev.get("entity", "")).lower():
                continue
            obs = ev.get("observed_at_chapter")
            window = ev.get("observed_window")
            in_scope = False
            if obs is not None and obs <= as_of_chapter:
                in_scope = True
            elif window:
                try:
                    lo, hi = (int(x) for x in str(window).split(".."))
                    # transition_unknown trong window: chỉ báo nếu N >= lo
                    in_scope = as_of_chapter >= lo
                except Exception:
                    pass
            if in_scope:
                out.append(ev)
        return out


class ArcLedger:
    """INV-8 — no personality drift without causal receipt.
    Project-scoped: storage/projects/<id>/arc_ledger.jsonl"""

    def __init__(self, project_dir: str):
        self.path = os.path.join(project_dir, "arc_ledger.jsonl")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def append(self, fic_chapter: int, character: str, dimension: str,
               from_state: str, to_state: str, causal_event: str,
               event_fic_chapter: int) -> Dict[str, Any]:
        rec = {
            "fic_ch": fic_chapter, "character": character, "dimension": dimension,
            "from": from_state, "to": to_state,
            "causal_event": causal_event, "event_fic_ch": event_fic_chapter,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def has_causal_receipt(self, character: str, dimension: str) -> Optional[Dict]:
        for rec in _load_jsonl(self.path):
            if rec.get("character") == character and rec.get("dimension") == dimension:
                return rec
        return None

    def all(self) -> List[Dict[str, Any]]:
        return _load_jsonl(self.path)
