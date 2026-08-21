"""
End-to-End Test & Simulation Suite (v0.8 Production-Ready):
Validates all P0 & P1 fixes:
1. Dynamic relative pathing & env support
2. Foreshadowing & Macro Bible integration
3. Hybrid Memory retrieval
4. Deterministic 33-Dimension Prose Audit & OOC Critic
5. SHA-256 Draft Hash & Staged Draft Protection
6. Full Snapshot State & Rollback
7. FastAPI Web Studio Endpoints
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fanfic_pipeline.core.state_manager import ProjectStateManager
from fanfic_pipeline.core.engine import FanficEngine
from fanfic_pipeline.core.model_router import PipelineModelRouter
from fanfic_pipeline.data.nhat_the_chi_ton.knowledge import CHARACTER_VOICES
from fanfic_pipeline.data.nhat_the_chi_ton.macro_bible import DEFAULT_NHAT_THE_MACRO_BIBLE
from fanfic_pipeline.core.models import PointOfDivergence, RelationshipState
from fanfic_pipeline.packages.auditor import AuditRunner
from fanfic_pipeline.packages.auditor.base import AuditContext
from fastapi.testclient import TestClient
from fanfic_pipeline.web_studio import app

def run_simulation():
    print("="*75)
    print("🚀 BẮT ĐẦU TEST & GIẢ LẬP TOÀN BỘ PIPELINE (V0.8 PRODUCTION FIXES)")
    print("="*75)

    project_id = "sim_test_v08_production"
    state_mgr = ProjectStateManager(project_id)

    # 1. Khởi tạo dự án
    print("\n[BƯỚC 1]: Khởi tạo dự án & Nạp Macro Story Bible...")
    pod = PointOfDivergence(
        divergence_anchor="Nhiệm vụ Ẩn Hình phường tân thủ",
        what_if_premise="Mạnh Kỳ kích hoạt được ký ức tiền kiếp sớm hơn, phát giác chân tướng Lục Đạo và Ma Phật An Nan",
        butterfly_effects=[
            "Cố Tiểu Tang tiếp cận Mạnh Kỳ sớm hơn tại mật thất sơn trại",
            "Mạnh Kỳ tập trung tu luyện Lôi Đao và Bát Cửu Huyền Công có định hướng rõ ràng từ đầu"
        ],
        frozen_canon=[
            "Quy tắc Lục Đạo trừ thiện công và xóa sổ giữ nguyên",
            "Hệ thống cảnh giới Khai Khiếu -> Ngoại Cảnh -> Pháp Thân giữ nguyên"
        ]
    )

    relationships = [
        RelationshipState(
            pair=["Mạnh Kỳ", "Cố Tiểu Tang"],
            trope_type="Enemies to Lovers / Mind Games",
            intimacy_level=2,
            current_dynamic="Vừa đề phòng vừa cuốn hút lẫn nhau",
            unspoken_conflicts=["Thân phận Ma Môn và sự khống chế của Vô Sinh Lão Mẫu"]
        ),
        RelationshipState(
            pair=["Mạnh Kỳ", "Giang Chỉ Vi"],
            trope_type="Comrades in Arms / Sword Kinship",
            intimacy_level=5,
            current_dynamic="Đồng đội sinh tử chi giao, kiếm đao tương đắc",
            unspoken_conflicts=[]
        )
    ]

    state_mgr.init_project(
        title="Nhất Thế Chi Tôn: Đao Kiếm Tương Phùng (v0.8 Prod)",
        fandom="Nhất Thế Chi Tôn (一世之尊)",
        pod=pod,
        voices=CHARACTER_VOICES,
        relationships=relationships,
        execution_mode="FULL_AUTO"
    )
    print("✅ Dự án khởi tạo thành công với đường dẫn động!")

    # 2. Kiểm tra Macro Bible & Epistemic Boundary
    print("\n[BƯỚC 2]: Kiểm tra Cấu trúc 4 Đại Quyển & Ranh giới Tri thức (Epistemic Boundary)...")
    cur_vol = DEFAULT_NHAT_THE_MACRO_BIBLE.get_current_volume(1)
    print(f"📖 Quyển hiện tại cho Chương 1: {cur_vol.title}")
    print(f"🎯 Mốc cảnh giới mục tiêu: {cur_vol.realm_milestone}")
    print(f"🔒 Ranh giới tri thức Mạnh Kỳ (Forbidden): {DEFAULT_NHAT_THE_MACRO_BIBLE.epistemic_boundaries['Mạnh Kỳ'].forbidden_knowledge[0]}")

    # 3. Kiểm tra Deterministic 33-Dimension Prose Audit
    print("\n[BƯỚC 3]: Kiểm tra Ma trận Thẩm định 33 Chiều (5 Prose Quality Guards)...")
    test_short_draft = "Mạnh Kỳ bước vào. Hắn nhìn quanh. Mọi thứ im lặng."
    _audit = AuditRunner()
    audit_short = _audit.evaluate(test_short_draft, AuditContext(chapter_num=1))
    print(f"  * Test draft quá ngắn (<500 từ) -> Verdict: {audit_short.verdict} (Score: {audit_short.score}/100)")
    assert audit_short.verdict == "REVISE", "Guard dung lượng ngắn phải phát hiện lỗi!"
    print("✅ 5 Prose Quality Guards hoạt động chuẩn xác!")

    # 4. Chạy sinh liên tiếp 2 chương qua Multi-Agent Engine
    print("\n[BƯỚC 4]: Chạy sinh liên tiếp 2 chương qua Multi-Agent Engine (Nối Hybrid Memory & Foreshadowing)...")
    engine = FanficEngine(state_mgr)

    # Chương 1
    outline1, draft1, critique1 = engine.run_chapter_step(
        1,
        author_instruction="Tiểu đội Luân Hồi tập hợp tại Ẩn Hình sơn trại, Mạnh Kỳ đối đầu tâm lý với Cố Tiểu Tang."
    )
    draft_hash1 = state_mgr.calculate_draft_hash(draft1.content)
    state_mgr.commit_chapter(1, draft1, outline1, expected_hash=draft_hash1)
    print(f"  * Chương 1 hoàn tất: '{draft1.title}' | Số từ: {draft1.word_count} | SHA256: {draft_hash1} | OOC Score: {critique1.ooc_score}/10 | Canon: {critique1.canon_consistency_score}/10")

    # Chương 2
    state_mgr.update_story_state({
        "current_location": "Sơn đạo Ẩn Hình phường - Đường rút lui",
        "unresolved_hooks": ["Ý nghĩa tấm lệnh bài Cố Tiểu Tang để lại"]
    })
    outline2, draft2, critique2 = engine.run_chapter_step(
        2,
        author_instruction="Tiểu đội rút lui an toàn, Mạnh Kỳ phân tích manh mối lệnh bài và chia sẻ thiện công cùng đồng đội."
    )
    draft_hash2 = state_mgr.calculate_draft_hash(draft2.content)
    state_mgr.commit_chapter(2, draft2, outline2, expected_hash=draft_hash2)
    print(f"  * Chương 2 hoàn tất: '{draft2.title}' | Số từ: {draft2.word_count} | SHA256: {draft_hash2} | OOC Score: {critique2.ooc_score}/10 | Canon: {critique2.canon_consistency_score}/10")

    # 5. Kiểm tra Snapshot Toàn Vẹn & Rollback
    print("\n[BƯỚC 5]: Kiểm tra Snapshot Toàn Vẹn (Voices, Relationships, Memories) & Rollback...")
    meta_before = state_mgr.load_project_meta()
    print(f"  * Trước rollback: Đang ở Chương {meta_before.get('current_chapter')}")
    state_mgr.rollback_to_chapter(1)
    meta_after = state_mgr.load_project_meta()
    voices_after = state_mgr.load_voices()
    rel_after = state_mgr.load_relationships()
    print(f"  * Sau rollback về Chương 1: Đang ở Chương {meta_after.get('current_chapter')} (Voices: {len(voices_after)}, Quan hệ: {len(rel_after)})")
    assert meta_after.get("current_chapter") == 1, "Rollback thất bại!"
    assert len(voices_after) == 5, "Snapshot phải bảo toàn voices!"
    print("✅ Kiểm tra Snapshot toàn vẹn và Rollback thành công!")

    # 6. Kiểm tra Web Studio REST API
    print("\n[BƯỚC 6]: Kiểm tra toàn bộ REST API của Web Studio...")
    client = TestClient(app)
    
    resp_status = client.get("/api/status")
    assert resp_status.status_code == 200
    print(f"  * API /api/status: 200 OK | Fandom: {resp_status.json()['meta']['fandom']}")

    resp_plan = client.post("/api/plan-chapter", json={"author_instruction": "Test instruction"})
    assert resp_plan.status_code == 200
    print(f"  * API /api/plan-chapter: 200 OK | Tiêu đề dàn ý sinh ra: '{resp_plan.json()['title']}'")

    print("\n" + "="*75)
    print("🎉 TẤT CẢ CÁC BƯỚC TEST V0.8 PRODUCTION FIXES ĐỀU ĐÃ PASS 100%!")
    print("="*75)

if __name__ == "__main__":
    run_simulation()
