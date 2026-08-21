"""
Unit and Integration tests for Phase 2: Modular Audit System & Actionable Critic.
"""
import pytest
from fanfic_pipeline.packages.auditor.base import AuditContext, CheckResult, BaseChecker
from fanfic_pipeline.packages.auditor.registry import CheckerRegistry
from fanfic_pipeline.packages.auditor.runner import AuditRunner

def test_P2_T1_registry_loads_26_checkers():
    """P1 merge (spec 2026-08-21): registry mở rộng 19 → 26; epistemic_claim thay epistemic_leak."""
    registry = CheckerRegistry()
    checkers = registry.list_checkers()
    assert len(checkers) == 26
    ids = {c.checker_id for c in checkers}
    assert "word_count" in ids
    assert "alive_dead" in ids
    assert "realm_strictness" in ids
    assert "ooc_fidelity" in ids
    assert "epistemic_claim" in ids
    assert "meta_leak" in ids
    assert "transition_topology" in ids
    assert "style_fingerprint" in ids
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
    # Đoạn văn dài, câu 18-38 từ, đoạn 100-240 ký tự, không lặp nguyên văn
    paras = [
        ("Mạnh Kỳ đứng trên đỉnh núi cao nhìn mây trôi về phía chân trời xa xăm, tay "
         "siết nhẹ chuôi đao sau lưng. Lòng hắn bình thản như mặt hồ không gợn sóng, "
         "chỉ có gió lạnh thổi qua vạt áo mang theo hơi thở se se của mùa thu."),
        ("Dưới chân núi, dòng sông bạc, lấp lánh uốn quanh thung lũng xanh mướt. Vài "
         "cánh chim trắng chao liệng trên bầu trời rồi mất hút sau rặng thông cổ "
         "thụ, để lại tiếng vọng dài, ngân nga trong khoảng không tĩnh mịch."),
        ("Hắn nhớ lời sư phụ dặn dò trước lúc xuống núi hành đạo. Những lời khuyên "
         "giản dị, mà sâu sắc vẫn còn vang vọng bên tai, như nhắc nhở hắn phải luôn "
         "giữ vững bản tâm giữa cám dỗ danh lợi của giang hồ."),
        ("Thanh đao cũ kỹ trên lưng khẽ rung lên nhẹ nhàng, như thể cảm nhận được "
         "tâm trạng chủ nhân đang trầm tư suy nghĩ. Lớp vỏ gỗ sần sùi che giấu một "
         "lưỡi kiếm sắc lạnh, từng uống máu không ít cao thủ danh trấn một thời."),
        ("Chạng vạng tối, ánh hoàng hôn đỏ rực cuối cùng cũng tắt hẳn sau dãy núi "
         "trùng điệp. Bóng dáng gầy cao của Mạnh Kỳ in dài trên tấm đá bằng phẳng, "
         "tựa như một nét mực đậm giữa bức tranh thủy mặc rộng lớn mà thâm trầm."),
        ("Đêm xuống nhanh chóng, hắn nhóm một đống lửa nhỏ để sưởi ấm cơ thể giá "
         "lạnh. Ngọn lửa bập bùng phản chiếu trong đôi mắt sáng quắc đầy kiên định; "
         "mai đây hành trình mới bắt đầu, khó khăn nào cũng không ngăn được bước chân."),
        ("Nửa đêm, sương muối phủ trắng mặt cỏ quanh trại tạm, tiếng côn trùng rả "
         "rích cũng dần im bặt, chỉ còn lửa cháy xèo xèo và hơi nước bốc lên nghi "
         "ngút từ ống tre đựng nước đun sôi đặt cạnh đống than hồng âm ỉ."),
        ("Trước lúc nhắm mắt nghỉ ngơi, Mạnh Kỳ kiểm tra lại túi lương thực khô "
         "và bình nước, đếm số tiền bạc còn lại trong túi vải, tính toán lộ trình "
         "cho ba ngày tiếp theo rồi mới an tâm nhắm mắt, thả lỏng toàn thân ngủ say."),
        ("Bên bờ suối nhỏ chảy róc rách, một con hươu cao đầu thò đầu uống nước, "
         "đôi tai nó phe phẩy liên hồi, cảnh giác với mọi động tĩnh lạ thường xung "
         "quanh, chợt nghe tiếng người la, nó giật mình phóng vọt vào rừng mất dạng."),
        ("Ánh trăng non treo lơ lửng trên đỉnh núi phía đông, tỏa ánh sáng bạc mờ "
         "ảo xuống thung lũng sâu hun hút, phủ lên mọi vật một lớp khói sương mơ "
         "màng, huyền bí như chốn thần tiên trong những câu chuyện cũ kể lại."),
        ("Sáng hôm sau, hắn dậy từ khi trời còn mờ sương, cuộn lại tấm chăn mỏng "
         "rồi vội ra bờ suối rửa mặt, nước lạnh buốt làm tinh thần hắn tỉnh táo "
         "hẳn lên, khuôn mặt trẻ trung hiện rõ dưới ánh bình minh, đầy sức sống."),
    ]
    clean_draft = "\n\n".join(paras)
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

def test_P2_T6_audit_runner_fail_on_flight_violation():
    runner = AuditRunner()
    paras = [
        ("Mạnh Kỳ ngồi thiền điều khí trên tảng đá phẳng trước động phủ, nội lực "
         "tuần hoàn theo chu thiên thứ ba mươi sáu, từng luồng chân khí ấm áp len "
         "lỏi qua kinh mạch, nuôi dưỡng gân cốt, tẩy sạch tạp chất còn sót lại."),
        ("Khí hải trong người hắn sôi trào dữ dội hơn mọi lần, dòng chân khí dày "
         "đặc chảy qua các đại huyệt đạo, khiến mồ hôi trên trán hắn hóa thành hơi "
         "nước trắng mỏng, bay lên trong khí lạnh của đêm khuya núi rừng."),
        ("Trận pháp hộ sơn của tông môn ánh lên lớp quang mang nhạt màu xanh biếc, "
         "che chắn cả một vùng núi sâu an bình khỏi những kẻ dòm ngó bên ngoài, "
         "chỉ thỉnh thoảng lại vang lên tiếng kêu lạch cạch nhẹ nhàng kỳ lạ."),
        ("Canh ba, Mạnh Kỳ bỗng mở mắt, trong lòng dâng lên một quyết tâm mãnh liệt: "
         "hắn muốn thử thử thách thân pháp mà sư phụ vẫn cấm, dù biết rõ cảnh giới "
         "Khai Khiếu sơ kỳ của mình chưa đủ căn cơ để làm chuyện đó an toàn."),
        ("Mạnh Kỳ ngự không phi hành bay lên khỏi ngọn thông cổ thụ, gió đêm gào "
         "thét qua tai, rồi chân khí đứt quãng giữa không trung, cả người rơi tựa "
         "lá vàng xuống thảm cỏ ướt sương, đau điếng khắp xương cốt, hối hận vô cùng."),
    ]
    draft = "\n\n".join(paras)
    ctx = AuditContext(
        chapter_num=2,
        current_state={"character_realms": {"Mạnh Kỳ": "Khai Khiếu (Sơ kỳ - 1-4 Khiếu)"}}
    )
    receipt = runner.evaluate(draft, ctx)
    assert receipt.overall_passed is False
    assert receipt.verdict == "REVISE"
    assert any("REALM_STRICTNESS" in d for d in receipt.revision_directives)


def test_P2_T7_audit_runner_fail_on_epistemic_leak():
    """P1 merge: epistemic_leak nghỉ — epistemic_claim kế thừa secret-check từ packet."""
    class MockPacket:
        forbidden = ["Thân phận Lục Đạo Ma Phật"]

    runner = AuditRunner()
    paras = [
        ("Mạnh Kỳ đứng bên cửa sổ suy ngẫm về đạo tâm, tay gõ nhẹ lên mặt bàn gỗ theo "
         "nhịp thở đều đặn, ngoài kia tuyết rơi trắng xóa che khuất dãy núi thẳm."),
        ("Tiếng chuông chiều vẳng lại từ chùa cổ xa xăm, buồn bã mà thấm đượm, khiến "
         "hắn chợt nhớ tới những ngày tháng tu hành giản dị nơi chốn thiền môn."),
        ("Hồi ức về người bạn cũ vẫn còn nguyên vẹn trong ký ức, nụ cười hiền hậu và "
         "ánh mắt sáng ngời quyết tâm của người bạn năm xưa chưa bao giờ phai nhạt."),
        ("Nhưng rồi mọi suy tưởng bị một phát hiện chấn động kéo trở về hiện tại: "
         "Hắn bỗng nhiên nhận ra Thân phận Lục Đạo Ma Phật từ sớm."),
        ("Sự thật này quá lớn lao, quá bất ngờ, đến mức Mạnh Kỳ phải ngồi sụp xuống "
         "ghế đá, tim đập dồn dập như trống trận, mồ hôi lạnh lấm tấm trên trán."),
    ]
    draft = "\n\n".join(paras)
    ctx = AuditContext(chapter_num=2, writer_packet=MockPacket())
    receipt = runner.evaluate(draft, ctx)
    assert receipt.overall_passed is False
    assert receipt.verdict == "REVISE"
    assert any("EPISTEMIC_CLAIM" in d for d in receipt.revision_directives)
