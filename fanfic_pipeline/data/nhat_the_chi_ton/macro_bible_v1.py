"""
Master Macro Story Bible v1.1 (with Branch/Sealing/Rolling Horizon wiring):
4 Volumes & Story Arcs with Mini-Arcs, Foreshadowing Hooks, Epistemic Boundaries.
Backward compat with v1.0 API.
"""

from fanfic_pipeline.core.macro_architecture import VolumeArc, ForeshadowingHook, EpistemicBoundary, BeatContract, NarrativeDebt, NarrativeDebtLedger
from fanfic_pipeline.core.hierarchical_planner import HierarchicalStoryPlanner, StoryArc, MiniArc, SealedArc, RollingPlan

DEFAULT_VOLUMES = [
    VolumeArc(
        volume_number=1,
        title="Quyển 1: Luân Hồi Sơ Lâm & Giang Hồ Thập Bát Chiến",
        start_chapter=1,
        end_chapter=150,
        core_theme="Sinh tồn trong không gian Lục Đạo, lập tiểu đội và bái nhập danh môn",
        main_antagonist_or_force="Đóa Nhi Sát, Ma Môn Lục Đạo sơ kỳ, Áp lực xóa sổ của Lục Đạo",
        realm_milestone="Từ Khai Khiếu sơ kỳ đến Tề Khiếu viên mãn (Cửu Khiếu Tề Thông)",
        cp_milestone="Mạnh Kỳ x Cố Tiểu Tang: Thăm dò lẫn nhau, gieo mầm nhân duyên ma mị; Mạnh Kỳ x Giang Chỉ Vi: Kết nghĩa sinh tử đồng đội",
        major_turning_points=[
            "Nhiệm vụ Ẩn Hình sơn trại (Chương 1-10)",
            "Nhiệm vụ Đóa Nhi Sát & Khai Khiếu viên mãn (Chương 50-70)",
            "Đại chiến Hắc Lục giang (Chương 120-150)"
        ]
    ),
    VolumeArc(
        volume_number=2,
        title="Quyển 2: Ngoại Cảnh Phong Vân & Cửu Trọng Thiên Bí Ẩn",
        start_chapter=151,
        end_chapter=350,
        core_theme="Thiên Nhân Hợp Nhất, thăm dò tàn tích Thần Thoại và Cửu Trọng Thiên",
        main_antagonist_or_force="Bắc Trạch Chân Vũ phái, Thần Đô Triệu Thị thế gia, Thần Thoại & Tiên Tích tranh phong",
        realm_milestone="Đột phá Bán Bộ Ngoại Cảnh lên Ngoại Cảnh Thiên Nhân Hợp Nhất (Nhất Trọng đến Ngũ Trọng Thiên)",
        cp_milestone="Mạnh Kỳ & Cố Tiểu Tang cùng rơi vào hiểm cảnh Cửu Trọng Thiên, thấu hiểu nỗi tuyệt vọng của nhau",
        major_turning_points=[
            "Thiên Nhân Giao Cảm tại Thần Đô (Chương 180)",
            "Tiến vào di tích Cửu Trọng Thiên, đoạt Lôi Trì chi thủy (Chương 260)",
            "Mạnh Kỳ ngộ ra Bát Cửu Huyền Công đệ nhị tầng (Chương 320)"
        ]
    ),
    VolumeArc(
        volume_number=3,
        title="Quyển 3: Pháp Thân Chi Lộ & Trảm Đoạn Nhân Duyên",
        start_chapter=351,
        end_chapter=600,
        core_theme="Chứng đạo Pháp Thân, chống lại vận mệnh và cứu vớt Cố Tiểu Tang tại Linh Sơn",
        main_antagonist_or_force="Kim Mẫu (Vô Sinh Lão Mẫu), Ma Phật An Nan, Lục Đạo Luân Hồi Chi Chủ",
        realm_milestone="Từ Ngoại Cảnh Đỉnh Phong (Cửu Trọng Thiên) chứng đắc Địa Tiên / Thiên Tiên Pháp Thân",
        cp_milestone="POD Phá Vỡ Bi Kịch: Mạnh Kỳ nghịch chuyển càn khôn cứu sống Cố Tiểu Tang khỏi kết cục Linh Sơn vẫn lạc",
        major_turning_points=[
            "Đại chiến Linh Sơn Cổ Sát (Chương 480)",
            "Cắt đứt một phần khống chế của Vô Sinh Lão Mẫu (Chương 520)",
            "Chứng đắc Nguyên Thủy Pháp Thân, danh chấn Chân Thực Giới (Chương 580)"
        ]
    ),
    VolumeArc(
        volume_number=4,
        title="Quyển 4: Bỉ Ngạn Bàn Cờ & Chư Thiên Vạn Giới",
        start_chapter=601,
        end_chapter=1000,
        core_theme="Truyền Thuyết, Tạo Hóa, nhảy ra khỏi Khổ Hải, chứng đắc Đạo Quả",
        main_antagonist_or_force="Các cự đầu Bỉ Ngạn (A Di Đà, Bồ Đề, Đạo Tiêu Ma Trưởng)",
        realm_milestone="Truyền Thuyết (Vô Sở Bất Tri) -> Tạo Hóa -> Đăng Lâm Bỉ Ngạn",
        cp_milestone="Mạnh Kỳ & Cố Tiểu Tang đồng hành trên dòng sông thời gian, cùng chưởng quản Chân Thực Giới",
        major_turning_points=[
            "Điểm hóa Chư Thiên Hình Chiếu (Chương 700)",
            "Đại kiếp Mạt Pháp & Đạo Tiêu Ma Trưởng (Chương 850)",
            "Trảm Ma Phật, chứng Đạo Quả vô thượng (Chương 990-1000)"
        ]
    )
]

DEFAULT_ARCS = [
    StoryArc(
        arc_id="arc_01",
        volume_number=1,
        title="Phân đoạn 1: Tân Thủ Thí Luyện & Ẩn Hình Phường",
        start_chapter=1,
        end_chapter=20,
        arc_theme="Thành lập tiểu đội Luân Hồi, đối đầu sơn tặc và chạm trán Cố Tiểu Tang",
        main_antagonist="Thủ lĩnh Ẩn Hình phường & Sứ giả Tố Nữ Đạo",
        mini_arcs=[
            MiniArc(
                mini_arc_id="mini_01_01",
                title="Tập hợp Lục Đạo & Đột nhập Sơn trại",
                chapter_range=[1, 5],
                objective="Làm quen đồng đội, phân tích nhiệm vụ Lục Đạo, tập kích tiền đình sơn trại",
                escalation_beat="Phát hiện dấu vết công pháp Ma Môn trên thi thể hộ vệ",
                climax_payoff="Mạnh Kỳ vung Lôi Đao trảm sát đầu mục, đẩy lùi phục kích",
                exit_criteria="Tiểu đội tiến vào mật thất phía sau sơn trại"
            ),
            MiniArc(
                mini_arc_id="mini_01_02",
                title="Mật Thất Tao Ngộ & Khẩu Chiến Ma Nữ",
                chapter_range=[6, 10],
                objective="Đối mặt Cố Tiểu Tang tại mật thất, giành lệnh bài và giữ vững đạo tâm",
                escalation_beat="Cố Tiểu Tang dùng lời lẽ ma mị trêu chọc và thăm dò thân phận Mạnh Kỳ",
                climax_payoff="Mạnh Kỳ nhìn thấu tâm cơ, đoạt lệnh bài và rút lui an toàn",
                exit_criteria="Hoàn thành nhiệm vụ Lục Đạo và trở về an toàn"
            )
        ]
    )
]

DEFAULT_HOOKS = [
    ForeshadowingHook(
        hook_id="hook_001",
        description="Bí mật về chuỗi hạt Bồ Đề và ký ức Ma Phật An Nan trong thức hải Mạnh Kỳ",
        planted_chapter=1,
        target_harvest_chapter=150,
        urgency="high",
        status="planted",
        involved_characters=["Mạnh Kỳ", "Cố Tiểu Tang"]
    ),
    ForeshadowingHook(
        hook_id="hook_002",
        description="Lý tưởng Ma Hoàng bí truyền của Tề Chính Ngôn bị phát giác",
        planted_chapter=40,
        target_harvest_chapter=200,
        urgency="medium",
        status="planted",
        involved_characters=["Tề Chính Ngôn", "Mạnh Kỳ"]
    )
]

DEFAULT_EPISTEMIC = {
    "Mạnh Kỳ": EpistemicBoundary(
        character_name="Mạnh Kỳ",
        known_facts=["Mình là người chuyển sinh", "Lục Đạo là thế lực tàn nhẫn thao túng số phận", "Đồng đội hiện tại là những người đáng tin cậy"],
        false_beliefs=["Tưởng rằng mình chỉ vô tình bị Lục Đạo bắt chọn làm luân hồi giả"],
        forbidden_knowledge=["Chưa biết mình là 'ngư tử' (con mồi chuyển thế) của Ma Phật An Nan và Nguyên Thủy Thiên Tôn"]
    ),
    "Cố Tiểu Tang": EpistemicBoundary(
        character_name="Cố Tiểu Tang",
        known_facts=["Mình là hóa thân dự phòng của Kim Mẫu", "Mạnh Kỳ có nhân quả sâu xa với Ma Phật", "Muốn sống sót bắt buộc phải tìm kẽ hở giữa các đại năng"],
        false_beliefs=["Nghĩ rằng Mạnh Kỳ sẽ luôn theo đúng quỹ đạo bị thao túng"],
        forbidden_knowledge=["Chưa biết Mạnh Kỳ đã kích hoạt tri giác tiền kiếp sớm hơn nhờ điểm POD"]
    )
}

# Re-export for convenience
__all__ = [
    "DEFAULT_VOLUMES", "DEFAULT_ARCS", "DEFAULT_HOOKS", "DEFAULT_EPISTEMIC",
    "VolumeArc", "ForeshadowingHook", "EpistemicBoundary",
    "BeatContract", "NarrativeDebt", "NarrativeDebtLedger",
    "HierarchicalStoryPlanner", "StoryArc", "MiniArc", "SealedArc", "RollingPlan",
    "get_default_hierarchical_planner", "load_v2_if_available"
]

def load_v2_if_available(project_dir: Optional[str] = None) -> Tuple[List[VolumeArc], Dict[str, StoryArc]]:
    """Tải macro_bible_v2 nếu tồn tại trong project_dir hoặc data dir."""
    import os, json, pathlib
    paths = []
    if project_dir:
        paths.append(os.path.join(project_dir, "macro_bible_v2.json"))
        paths.append(os.path.join(project_dir, "data", "macro_bible_v2.json"))
    p_default = pathlib.Path(__file__).resolve().parent / "macro_bible_v2.json"
    paths.append(str(p_default))

    for p in paths:
        if os.path.exists(p):
            try:
                data = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
                vols = [VolumeArc(**v) for v in data.get("volumes", [])] if data.get("volumes") else DEFAULT_VOLUMES
                arcs = {}
                for aid, ad in data.get("arcs", {}).items():
                    arcs[aid] = StoryArc(
                        arc_id=aid,
                        title=ad.get("title", ""),
                        volume_id=ad.get("volume_id", "vol_01"),
                        chapter_range=(ad.get("start_chapter", 1), ad.get("end_chapter", 30)),
                        primary_objective=ad.get("objective", ""),
                        turning_points=ad.get("turning_points", [])
                    )
                if vols and arcs:
                    return vols, arcs
            except Exception:
                pass
    return DEFAULT_VOLUMES, DEFAULT_ARCS

def get_default_hierarchical_planner(branch_id: str = "main", project_dir: Optional[str] = None) -> HierarchicalStoryPlanner:
    vols, arcs = load_v2_if_available(project_dir)
    return HierarchicalStoryPlanner(
        volumes=vols,
        arcs=arcs,
        hooks=DEFAULT_HOOKS,
        epistemic=DEFAULT_EPISTEMIC,
        branch_id=branch_id,
    )

def get_default_debt_ledger(branch_id: str = "main") -> NarrativeDebtLedger:
    planner = get_default_hierarchical_planner(branch_id=branch_id)
    return planner.debt_ledger

