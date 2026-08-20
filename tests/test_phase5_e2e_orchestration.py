import pytest, tempfile
from fanfic_pipeline.core.state_manager import ProjectStateManager
from fanfic_pipeline.core.engine import FanficEngine
from fanfic_pipeline.core.models import PointOfDivergence

def test_P5_T1_end_to_end_chapter_step():
    tmp_dir = tempfile.mkdtemp()
    mgr = ProjectStateManager(project_id="test_e2e", base_dir=tmp_dir)
    pod = PointOfDivergence(
        divergence_anchor="Nhiệm vụ tân thủ Luân Hồi",
        what_if_premise="Mạnh Kỳ quyết định tu luyện Lôi Đao và Bát Cửu Huyền Công từ đầu.",
        butterfly_effects=[],
        frozen_canon=[]
    )
    mgr.init_project(title="Test E2E", fandom="Nhất Thế Chi Tôn", pod=pod, voices={}, relationships=[])

    engine = FanficEngine(mgr)
    outline, draft, critique, delta = engine.run_chapter_step(
        chapter_num=1,
        author_instruction="Giao tranh với sát thủ Ẩn Hình Phường"
    )

    assert outline.chapter_number == 1
    assert len(outline.scene_beats) >= 1
    assert draft.chapter_number == 1
    assert len(draft.content) > 100
    assert critique is not None
    assert delta is not None

def test_P5_T2_end_to_end_atomic_commit():
    tmp_dir = tempfile.mkdtemp()
    mgr = ProjectStateManager(project_id="test_e2e_commit", base_dir=tmp_dir)
    pod = PointOfDivergence(
        divergence_anchor="Chương 1",
        what_if_premise="Test",
        butterfly_effects=[],
        frozen_canon=[]
    )
    mgr.init_project(title="Test E2E Commit", fandom="Nhất Thế Chi Tôn", pod=pod, voices={}, relationships=[])

    engine = FanficEngine(mgr)
    outline, draft, critique, delta = engine.run_chapter_step(chapter_num=1)
    
    commit_res = engine.commit_chapter(1, draft, outline, delta)
    assert commit_res["status"] == "COMMITTED"
    assert commit_res["chapter_number"] == 1

