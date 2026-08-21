"""
P3 — Intel: Social Web (arc-scoped relationship bible) + OC Power System.

- social_web.py (module này): bible quan hệ theo arc; chapter spec khai
  social_targets; thiếu target = BLOCK; writer chỉ thấy beat hiện tại.
- oc_power.py: availability ≠ acquisition ≠ mastery ≠ realm; survival floor.
Cả hai đọc từ project storage (schema port từ reference, dữ liệu của project).
"""
import json
import os
from typing import Any, Dict, List, Optional


def _load_json(path: str) -> Optional[Dict[str, Any]]:
    if os.path.exists(path):
        try:
            return json.loads(open(path, encoding="utf-8").read())
        except Exception:
            return None
    return None


class SocialWeb:
    """Project-scoped social bible: storage/projects/<id>/social/<arc>.json"""

    def __init__(self, project_dir: str):
        self.base = os.path.join(project_dir, "social")

    def resolve(self, arc_id: str, targets: List[Dict[str, Any]],
                as_of_fic_ch: int, mode: str = "writer") -> Dict[str, Any]:
        """mode='writer': chỉ trả beat hiện tại + quá khứ; future beats bị giấu.
        Trả {status, resolved, missing, context}."""
        bible = None
        if arc_id:
            for ext in ("", ".json"):
                p = os.path.join(self.base, f"{arc_id}{ext}")
                if os.path.exists(p):
                    bible = _load_json(p)
                    break
        if bible is None:
            if not targets:
                return {"status": "N/A_WITH_REASON",
                        "reason": "chapter spec không khai social_targets"}
            return {"status": "BLOCK",
                    "missing": [t.get("name", str(t)) for t in targets],
                    "reason": f"social bible '{arc_id}' không tồn tại"}
        resolved, missing = [], []
        for t in targets:
            name = t.get("name") or t.get("entity")
            entry = (bible.get("relationships") or {}).get(name) \
                if isinstance(bible.get("relationships"), dict) else None
            if entry is None:
                missing.append(name)
                continue
            reveal_ch = entry.get("reveal_fic_ch")
            if reveal_ch and as_of_fic_ch < reveal_ch:
                missing.append(f"{name} (spoiler-hidden trước ch{reveal_ch})")
                continue
            beats = entry.get("beats") or []
            visible_beats = [b for b in beats
                             if not b.get("fic_ch") or b["fic_ch"] <= as_of_fic_ch]
            resolved.append({"target": name,
                             "current_beat": visible_beats[-1] if visible_beats else None})
        status = "USED" if resolved and not missing else (
            "BLOCK" if missing else "N/A_WITH_REASON")
        return {"status": status, "resolved": resolved, "missing": missing,
                "context": "\n".join(
                    f"- {r['target']}: {(r['current_beat'] or {}).get('state', '?')}"
                    for r in resolved)}


class OCPowerSystem:
    """Project-scoped OC power state: storage/projects/<id>/oc_power.json +
    power_acquisition_ledger.jsonl. Nguyên tắc: availability ≠ acquisition ≠
    mastery ≠ realm. Survival floor cho nhiệm vụ tử địa."""

    def __init__(self, project_dir: str):
        self.system_path = os.path.join(project_dir, "oc_power.json")
        self.ledger_path = os.path.join(project_dir, "power_acquisition_ledger.jsonl")

    def context_for_writer(self, as_of_fic_ch: int) -> Dict[str, Any]:
        system = _load_json(self.system_path)
        if not system:
            return {"status": "N/A_WITH_REASON", "reason": "project không khai OC power system"}
        acquisitions = self._acquisitions_as_of(as_of_fic_ch)
        return {
            "status": "USED",
            "realm": system.get("realm"),
            "root": system.get("root"),
            # Writer KHÔNG được thấy candidates tương lai (planner-only)
            "acquired": acquisitions,
            "candidates_hidden_from_writer": True,
        }

    def context_for_planner(self) -> Dict[str, Any]:
        system = _load_json(self.system_path)
        if not system:
            return {"status": "N/A_WITH_REASON", "reason": "no OC power system"}
        return {"status": "USED", **system,
                "candidates": system.get("candidate_abilities", [])}

    def _acquisitions_as_of(self, fic_ch: int) -> List[Dict[str, Any]]:
        out = []
        if os.path.exists(self.ledger_path):
            for line in open(self.ledger_path, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if int(rec.get("committed_at_fic_ch", 10**9)) <= fic_ch:
                    out.append(rec)
        return out

    def check_survival_floor(self, mission_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Nhiệm vụ tử địa phải có survival receipt READY trước khi viết."""
        if not mission_meta.get("lethal_mission"):
            return {"status": "N/A_WITH_REASON", "reason": "không phải nhiệm vụ tử địa"}
        receipt = mission_meta.get("survival_receipt")
        if receipt and receipt.get("verdict") == "READY":
            return {"status": "READY"}
        return {"status": "BLOCK",
                "reason": "survival-readiness receipt chưa READY — balance có sàn, "
                          "không balance bằng bất lực (spec §4.2)"}
