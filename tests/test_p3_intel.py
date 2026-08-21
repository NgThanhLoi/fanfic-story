"""
P3 Intel — Test đối kháng (spec §6 P3).

- Spoiler-reveal: bí danh trước reveal_chapter bị chặn (identity + checker)
- Candidate leak: writer context không được thấy future candidates
- Survival floor: nhiệm vụ tử địa thiếu receipt ⇒ BLOCK
- Personality drift không receipt ⇒ ooc/relationship chặn qua voice_rules
- Social web: thiếu target ⇒ BLOCK; spoiler-hidden target ⇒ BLOCK
"""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fanfic_pipeline.packages.intel import (
    IdentityResolver, CapabilityTimeline, ArcLedger, SocialWeb, OCPowerSystem,
)
from fanfic_pipeline.packages.auditor.checkers.identity_reveal import IdentityRevealChecker
from fanfic_pipeline.packages.auditor.checkers.ooc_fidelity import OOCFidelityChecker
from fanfic_pipeline.packages.auditor.base import AuditContext


class TestIdentity:
    def test_surfaces_hidden_before_reveal(self):
        res = IdentityResolver()
        early = res.surfaces_for("孟奇", as_of_chapter=100)
        late = res.surfaces_for("孟奇", as_of_chapter=300)
        early_ids = {s["identity_id"] for s in early}
        late_ids = {s["identity_id"] for s in late}
        # Tô Mạnh reveal ch.218: phải ẩn ở ch.100, lộ ở ch.300
        assert "ID-MQ-SUMENG" not in early_ids
        assert "ID-MQ-SUMENG" in late_ids

    def test_prose_violation_detected(self):
        res = IdentityResolver()
        v = res.check_prose("Tô Mạnh bước vào quán rượu.", as_of_chapter=100)
        assert any(x["surface"] == "Tô Mạnh" for x in v)

    def test_checker_blocks_spoiler_alias(self):
        ctx = AuditContext(current_state={"canon_time_max": 100})
        r = IdentityRevealChecker().check("Tô Mạnh ngồi xuống uống trà.", ctx)
        assert r.status == "FAIL"


class TestCapability:
    def test_time_indexed_query(self):
        cap = CapabilityTimeline()
        # Cố Tiểu Tang divination: observed ch.42 self_reports_no_understanding
        evs = cap.capabilities_as_of("Cố Tiểu Tang", as_of_chapter=42)
        assert evs, "phải thấy event đã quan sát tại ch.42"
        states = {e.get("state") for e in evs}
        assert "self_reports_no_divination_understanding" in states


class TestArcLedger:
    def test_drift_requires_receipt(self):
        """INV-8: drift tính cách không có causal receipt ⇒ checker chặn khi
        project khai rule; có receipt thì arc_ledger ghi nhận hợp lệ."""
        tmp = tempfile.mkdtemp(prefix="arc_")
        try:
            ledger = ArcLedger(tmp)
            assert ledger.has_causal_receipt("Mạnh Kỳ", "trust_toward_CTT") is None
            ledger.append(fic_chapter=5, character="Mạnh Kỳ", dimension="trust_toward_CTT",
                          from_state="cảnh giác", to_state="tin một phần",
                          causal_event="Cô ta che sau lưng hắn trong trận phục kích",
                          event_fic_chapter=4)
            rec = ledger.has_causal_receipt("Mạnh Kỳ", "trust_toward_CTT")
            assert rec and rec["event_fic_ch"] == 4
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_ooc_checker_enforces_custom_rule_without_receipt(self):
        ctx = AuditContext(current_state={"voice_rules": {
            "Cố Tiểu Tang": [{"pattern": r"(?i)Cố\s+Tiểu\s+Tang.{0,30}tin\s+tưởng\s+tuyệt\s+đối",
                               "reason": "drift trust không có receipt (arc_ledger rỗng)"}]}})
        r = OOCFidelityChecker().check(
            "Cố Tiểu Tang thừa nhận nàng tin tưởng tuyệt đối vào Mạnh Kỳ.", ctx)
        assert r.status == "FAIL"


class TestSocialWeb:
    def test_block_when_bible_missing_with_targets(self):
        tmp = tempfile.mkdtemp(prefix="sw_")
        try:
            sw = SocialWeb(tmp)
            out = sw.resolve("ARC_01", [{"name": "Giang Chỉ Vi"}], as_of_fic_ch=3)
            assert out["status"] == "BLOCK"
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_na_when_no_targets(self):
        tmp = tempfile.mkdtemp(prefix="sw_")
        try:
            sw = SocialWeb(tmp)
            out = sw.resolve(None, [], as_of_fic_ch=3)
            assert out["status"] == "N/A_WITH_REASON"
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_writer_sees_only_past_beats(self):
        tmp = tempfile.mkdtemp(prefix="sw_")
        try:
            os.makedirs(os.path.join(tmp, "social"))
            bible = {"relationships": {"Giang Chỉ Vi": {
                "reveal_fic_ch": 1,
                "beats": [
                    {"fic_ch": 2, "state": "đồng đội tin cậy"},
                    {"fic_ch": 20, "state": "tình cảm sâu đậm"},
                ]}}}
            with open(os.path.join(tmp, "social", "ARC_01.json"), "w") as f:
                json.dump(bible, f)
            sw = SocialWeb(tmp)
            out = sw.resolve("ARC_01", [{"name": "Giang Chỉ Vi"}], as_of_fic_ch=5,
                             mode="writer")
            assert out["status"] == "USED"
            assert out["resolved"][0]["current_beat"]["state"] == "đồng đội tin cậy"
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spoiler_hidden_target_blocks(self):
        tmp = tempfile.mkdtemp(prefix="sw_")
        try:
            os.makedirs(os.path.join(tmp, "social"))
            bible = {"relationships": {"Bách Biến Thư Sinh": {
                "reveal_fic_ch": 33, "beats": []}}}
            with open(os.path.join(tmp, "social", "ARC_01.json"), "w") as f:
                json.dump(bible, f)
            sw = SocialWeb(tmp)
            out = sw.resolve("ARC_01", [{"name": "Bách Biến Thư Sinh"}], as_of_fic_ch=10)
            assert out["status"] == "BLOCK"
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class TestOCPower:
    def test_writer_cannot_see_candidates(self):
        tmp = tempfile.mkdtemp(prefix="oc_")
        try:
            system = {"realm": "Khai Khiếu — Nhãn Khiếu sơ khai", "root": "Vô Tướng Lâu",
                      "candidate_abilities": ["Thiên Hành Bách Biến (chưa thu nhận)"]}
            with open(os.path.join(tmp, "oc_power.json"), "w") as f:
                json.dump(system, f)
            oc = OCPowerSystem(tmp)
            wctx = oc.context_for_writer(as_of_fic_ch=15)
            assert wctx["candidates_hidden_from_writer"] is True
            assert "candidate_abilities" not in wctx
            pctx = oc.context_for_planner()
            assert pctx["candidates"]
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_survival_floor_blocks_lethal_mission(self):
        tmp = tempfile.mkdtemp(prefix="oc_")
        try:
            oc = OCPowerSystem(tmp)
            out = oc.check_survival_floor({"lethal_mission": True})
            assert out["status"] == "BLOCK"
            out2 = oc.check_survival_floor({
                "lethal_mission": True,
                "survival_receipt": {"verdict": "READY"}})
            assert out2["status"] == "READY"
            out3 = oc.check_survival_floor({"lethal_mission": False})
            assert out3["status"] == "N/A_WITH_REASON"
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_acquisition_needs_committed_ledger_entry(self):
        tmp = tempfile.mkdtemp(prefix="oc_")
        try:
            system = {"realm": "Khai Khiếu"}
            with open(os.path.join(tmp, "oc_power.json"), "w") as f:
                json.dump(system, f)
            with open(os.path.join(tmp, "power_acquisition_ledger.jsonl"), "w") as f:
                f.write(json.dumps({"ability": "Thiên Hành Bách Biến",
                                    "committed_at_fic_ch": 11}) + "\n")
            oc = OCPowerSystem(tmp)
            before = oc.context_for_writer(as_of_fic_ch=10)
            after = oc.context_for_writer(as_of_fic_ch=12)
            assert before["acquired"] == []
            assert after["acquired"][0]["ability"] == "Thiên Hành Bách Biến"
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
