"""
Unit and Integration tests for Phase 2: Modular Audit System & Actionable Critic.
"""
import pytest
from fanfic_pipeline.packages.auditor.base import AuditContext, CheckResult, BaseChecker
from fanfic_pipeline.packages.auditor.registry import CheckerRegistry
from fanfic_pipeline.packages.auditor.runner import AuditRunner

def test_P2_T1_registry_loads_19_checkers():
    registry = CheckerRegistry()
    checkers = registry.list_checkers()
    assert len(checkers) == 19
    ids = {c.checker_id for c in checkers}
    assert "word_count" in ids
    assert "alive_dead" in ids
    assert "realm_strictness" in ids
    assert "ooc_fidelity" in ids
    assert "epistemic_leak" in ids
    assert "ai_pattern" in ids

def test_P2_T2_base_checker_interface():
    res = CheckResult(
        checker_id="test", status="FAIL", severity="P0", score=0.0,
        reason="Test fail", actionable_fix="Fix line 5"
    )
    assert res.checker_id == "test"
    assert res.status == "FAIL"
    assert res.actionable_fix == "Fix line 5"

def test_P2_T3_audit_runner_pass_clean_draft():
    runner = AuditRunner()
    clean_draft = "Mạnh Kỳ đứng trên đỉnh núi nhìn mây trôi. " * 65
    ctx = AuditContext(chapter_num=1)

    receipt = runner.evaluate(clean_draft, ctx)
    assert receipt.overall_passed is True
    assert receipt.verdict == "PASS"

def test_P2_T4_audit_runner_fail_closed_on_dead_char():
    runner = AuditRunner()
    draft = ("Mạnh Kỳ nhìn về phía xa. " * 30) + "Huyền Tâm bước ra cười ha hả nói chuyện vui vẻ."
    ctx = AuditContext(
        chapter_num=2,
        current_state={"dead_characters": ["Huyền Tâm"]}
    )
    receipt = runner.evaluate(draft, ctx)
    assert receipt.overall_passed is False
    assert receipt.verdict == "REVISE"
    assert any("ALIVE_DEAD" in d for d in receipt.revision_directives)

def test_P2_T5_audit_runner_fail_on_ooc():
    runner = AuditRunner()
    draft = ("Mạnh Kỳ đối đầu địch nhân. " * 30) + "Mạnh Kỳ tuyệt vọng khóc lóc quỳ xuống xin tha mạng trước mặt kẻ địch."
    ctx = AuditContext(chapter_num=2)
    receipt = runner.evaluate(draft, ctx)
    assert receipt.overall_passed is False
    assert receipt.verdict == "REVISE"
    assert any("OOC_FIDELITY" in d for d in receipt.revision_directives)

def test_P2_T6_audit_runner_fail_on_flight_violation():
    runner = AuditRunner()
    draft = ("Mạnh Kỳ vận công. " * 30) + "Mạnh Kỳ ngự không phi hành bay thẳng lên chín tầng mây."
    ctx = AuditContext(
        chapter_num=2,
        current_state={"character_realms": {"Mạnh Kỳ": "Khai Khiếu (Sơ kỳ - 1-4 Khiếu)"}}
    )
    receipt = runner.evaluate(draft, ctx)
    assert receipt.overall_passed is False
    assert receipt.verdict == "REVISE"
    assert any("REALM_STRICTNESS" in d for d in receipt.revision_directives)

def test_P2_T7_audit_runner_fail_on_epistemic_leak():
    class MockPacket:
        forbidden = ["Thân phận Lục Đạo Ma Phật"]

    runner = AuditRunner()
    draft = ("Mạnh Kỳ suy ngẫm. " * 30) + "Hắn bỗng nhiên nhận ra Thân phận Lục Đạo Ma Phật từ sớm."
    ctx = AuditContext(chapter_num=2, writer_packet=MockPacket())
    receipt = runner.evaluate(draft, ctx)
    assert receipt.overall_passed is False
    assert receipt.verdict == "REVISE"
    assert any("EPISTEMIC_LEAK" in d for d in receipt.revision_directives)

def test_P2_T8_ai_pattern_preserves_authentic_tropes():
    runner = AuditRunner()
    # Draft with authentic Chinese Xianxia reaction tropes: must NOT be penalized
    draft = ("Mạnh Kỳ rút đao chém đứt tảng đá. " * 30) + "Đối thủ khóe miệng giật giật, hít một ngụm khí lạnh, đồng tử co rút nhìn chằm chằm thanh đao."
    ctx = AuditContext(chapter_num=2)
    receipt = runner.evaluate(draft, ctx)
    res_map = {r.checker_id: r.status for r in receipt.check_results}
    assert res_map["ai_pattern"] == "PASS"
