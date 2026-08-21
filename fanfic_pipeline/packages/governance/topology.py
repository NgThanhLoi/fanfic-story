"""
Governance P0 — Canonical transition topology (INV-1, review F-09).

Premise/planning artifact phải được canon-validate TRƯỚC khi trở thành đầu vào
tin cậy. Validator này chạy ở READINESS (prewrite), không chờ post-draft.
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import unicodedata


def _vi_strip_map() -> dict:
    src = ("áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợ"
           "úùủũụưứừửữựýỳỷỹỵđÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ")
    out = {}
    for ch in src:
        base = "".join(c for c in unicodedata.normalize("NFD", ch)
                       if unicodedata.category(c) != "Mn").lower()
        out[ch] = base or ch.lower()
    return out


_VI_STRIP = {ord(k): v for k, v in _vi_strip_map().items()}


def normalize_vi(text: str) -> str:
    return text.lower().translate(_VI_STRIP).replace("  ", " ").strip()


class TopologyViolation:
    def __init__(self, kind: str, message: str, detail: Optional[Dict[str, Any]] = None):
        self.kind = kind          # skip_transition | domain_fill | unknown_aperture
        self.message = message
        self.detail = detail or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "message": self.message, **self.detail}


class TransitionTopology:
    """Đọc aperture_topology.json; validate chuỗi khai-khiếu của planning artifact."""

    def __init__(self, topology_path: str):
        self.path = topology_path
        data = json.loads(Path(topology_path).read_text(encoding="utf-8"))
        self.order: List[str] = data["aperture_order"]
        self.nodes: Dict[str, Any] = data["nodes"]
        self.edges = {(e["from"], e["to"]) for e in data["edges"]}
        self.forbidden_skips = {s["skip"] for s in data.get("forbidden_skips", [])}
        self.dfg = data.get("domain_fill_guard", {})
        # name (normalized) -> node id; dài trước ngắn để match greedy
        self._name_map: List[Tuple[str, str]] = []
        for node_id, spec in self.nodes.items():
            for name in spec.get("vi_names", []):
                self._name_map.append((normalize_vi(name), node_id))
        self._name_map.sort(key=lambda x: -len(x[0]))
        self._blocked_terms = [normalize_vi(t) for t in self.dfg.get("blocked_tcm_terms", [])]

    # ---- parsing ----
    def extract_opened(self, text: str) -> List[str]:
        """Trích danh sách khiếu được TUYÊN BỐ đã mở/khai trong văn bản planning."""
        norm = normalize_vi(text)
        found: List[str] = []
        for name, node in self._name_map:
            if node in found:
                continue
            for verb in ("mo ", "khai "):
                idx = 0
                while True:
                    i = norm.find(verb + name, idx)
                    if i < 0:
                        break
                    # từ đứng trước không phải phủ định
                    # cửa sổ phủ định phải phủ cả động từ ("chưa khai", "không thể mở")
                    window = norm[max(0, i - 14):i + len(verb)]
                    if not any(neg in window for neg in ("chua ", "khong ", "chua bao gio")):
                        found.append(node)
                        break
                    idx = i + 1
        # giữ thứ tự canon
        return [n for n in self.order if n in found]

    def find_domain_fill(self, text: str) -> List[str]:
        """Tìm thuật ngữ TCM bị cấm (chưa có canonicalization receipt)."""
        norm = normalize_vi(text)
        return [term for term in self._blocked_terms if term in norm]

    # ---- validation ----
    def validate_progression(self, opened: List[str], target: Optional[str],
                             exception_receipts: Optional[List[str]] = None) -> List[TopologyViolation]:
        """opened: các khiếu đã committed-mở (thứ tự canon). target: khiếu chuẩn bị khai.
        Trả về danh sách vi phạm; rỗng = PASS."""
        receipts = set(exception_receipts or [])
        violations: List[TopologyViolation] = []

        # 1. opened phải là prefix hợp lệ của order
        expected_prefix = self.order[: len(opened)]
        if opened and opened != expected_prefix:
            violations.append(TopologyViolation(
                "skip_transition",
                f"Trạng thái đã mở {opened} không phải tiền tố hợp lệ của thứ tự canon {self.order}",
                {"opened": opened, "canonical_order": self.order},
            ))

        # 2. target phải là cạnh hợp lệ từ khiếu cuối đã mở
        if target is not None:
            if target not in self.order:
                violations.append(TopologyViolation(
                    "unknown_aperture", f"'{target}' không phải khiếu hợp lệ trong topology",
                    {"valid": self.order}))
            else:
                base = opened[-1] if opened else None
                if base is None:
                    first_ok = self.order[0]
                    if target != first_ok:
                        violations.append(TopologyViolation(
                            "skip_transition",
                            f"Chưa mở khiếu nào nhưng target='{target}' — phải bắt đầu từ '{first_ok}'",
                            {"target": target}))
                elif (base, target) not in self.edges:
                    skip_key = f"{base}->{target}"
                    if skip_key in self.forbidden_skips:
                        reason = next(s["reason"] for s in
                                      json.loads(Path(self.path).read_text(encoding="utf-8"))["forbidden_skips"]
                                      if s["skip"] == skip_key)
                    else:
                        reason = "không có cạnh canon"
                    if f"exception:{skip_key}" not in receipts:
                        violations.append(TopologyViolation(
                            "skip_transition",
                            f"Chuyển '{base}' → '{target}' vi phạm topology ({reason}). "
                            f"Cần exception receipt 'exception:{skip_key}'.",
                            {"from": base, "to": target, "legal_next": self._next_of(base)}))
        return violations

    def _next_of(self, node: str) -> Optional[str]:
        for a, b in self.edges:
            if a == node:
                return b
        return None

    def validate_artifact(self, artifact_text: str,
                          committed_opened: List[str],
                          exception_receipts: Optional[List[str]] = None) -> List[TopologyViolation]:
        """Validate một planning artifact (chapter spec / outline / scene dossier):
        - mọi khiếu tuyên bố MỚI so với committed phải theo cạnh hợp lệ;
        - cấm domain-fill TCM chưa canonicalize."""
        violations: List[TopologyViolation] = []
        declared = self.extract_opened(artifact_text)
        new_ones = [n for n in declared if n not in committed_opened]
        # "ngưng tụ quanh X" / "chuẩn bị X" cũng là khai báo TARGET (bài học FC36:
        # premise sai nằm ở planning 'ngưng luyện Tỵ Khiếu' chứ không cần chữ 'khai').
        if not new_ones:
            norm = normalize_vi(artifact_text)
            prep: List[str] = []
            for name, node in self._name_map:
                if node in committed_opened or node in prep:
                    continue
                # động từ chuẩn-bị và tên khiếu có thể cách nhau ("ngưng tụ các huyệt
                # đạo quanh Tỵ Khiếu") — cho phép cửa sổ ≤ 40 ký tự giữa verb và name.
                for verb in ("ngung tu ", "ngung luyen ", "chuan bi ", "tieu dung "):
                    start = 0
                    while True:
                        i = norm.find(verb, start)
                        if i < 0:
                            break
                        j = norm.find(name, i + len(verb))
                        if 0 <= j - (i + len(verb)) <= 40:
                            prep.append(node)
                            break
                        start = i + 1
                    if node in prep:
                        break
            new_ones = [n for n in self.order if n in prep]
        target = new_ones[-1] if new_ones else None
        violations.extend(self.validate_progression(committed_opened, target, exception_receipts))
        for term in self.find_domain_fill(artifact_text):
            violations.append(TopologyViolation(
                "domain_fill",
                f"Thuật ngữ ngoài-canon '{term}' xuất hiện mà không có canonicalization receipt "
                f"(bài học review F-02: cấm điền khoảng trống canon bằng huyệt TCM)",
                {"term": term}))
        return violations


def load_default_topology() -> Optional[TransitionTopology]:
    p = os.path.join(os.path.dirname(__file__), "..", "..", "data",
                     "nhat_the_chi_ton", "aperture_topology.json")
    p = os.path.normpath(p)
    if os.path.exists(p):
        return TransitionTopology(p)
    return None
