"""
Default Macro Story Bible for Long-form Fanfic (100 - 1000 Chapters)
Target: Nhất Thế Chi Tôn (一世之尊)
"""

from fanfic_pipeline.core.macro_architecture import MacroStoryBible, VolumeArc, ForeshadowingHook, EpistemicBoundary

DEFAULT_NHAT_THE_MACRO_BIBLE = MacroStoryBible(
    fandom="Nhất Thế Chi Tôn (一世之尊)",
    total_planned_volumes=4,
    volumes=[
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
                "Đại chiến Hắc Lục giang & Lần đầu chạm trán Cố Tiểu Tang thực lực đỉnh phong (Chương 120-150)"
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
    ],
    active_foreshadowings=[
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
    ],
    epistemic_boundaries={
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
)
