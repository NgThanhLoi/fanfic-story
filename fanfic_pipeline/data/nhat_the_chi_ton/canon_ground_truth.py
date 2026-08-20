"""
Authoritative Ground Truth Lore for 'Nhất Thế Chi Tôn' (一世之尊).
Derived from author Cuttlefish That Loves Diving's official setting & taxonomy.
"""
from typing import Dict, List, Any
from pydantic import BaseModel

FACTIONS_GROUND_TRUTH = {
    "Chính Đạo Cửu Đại Tông Môn": [
        "Thiếu Lâm Tự (A Di Đà Phật / Như Lai truyền thừa)",
        "Tẩy Kiếm Các (Tô Vô Danh, Giang Chỉ Vi - Trảm Đoạn Chấp Niệm, Kiếm Xuất Vô Hối)",
        "Chân Võ Tông (Trương Tam Phong / Đạo Môn Đạo Đức Thiên Tôn)",
        "Huyền Thiên Tông (Thiên Đế truyền thừa, Thời Gian Chi Đao)",
        "Côn Luân Sơn Ngọc Hư Cung (Nguyên Thủy Thiên Tôn)",
        "Bát Hoang Tiên Giới / Lang Nha Nguyễn Thị (Âm Luật Thần Thông)",
        "Hoàng Cơ Thần Triều (Triệu Hằng - Hoàng Long Ngọc Tỷ)"
    ],
    "Lục Đại Ma Môn": [
        "Tố Nữ Đạo (Vô Sinh Lão Mẫu / Cố Tiểu Tang)",
        "Diệt Thiên Môn (Lục Đạo Ma Quân / Diệt Thiên Ma Đao)",
        "Hoan Hỷ Thiền (Tà Thiền bí thuật)",
        "Bất Tử Yêu Đạo (Yêu Tộc tàn hồn)",
        "Tu La Đạo (Sát phạt thành đạo)",
        "Huyết Hải Giáo (U Minh Huyết Hải)"
    ]
}

DIVINE_MARTIAL_ARTS = {
    "Như Lai Thần Chưởng": "Cửu Thức Thần Chưởng trấn áp vạn giới, do Phật Tổ sáng lập (Duy Ngã Độc Tôn, Chưởng Trung Tịnh Thổ).",
    "Tiệt Thiên Thất Kiếm": "Thất thức kiếm ý trảm đoạn thiên đạo quy tắc, do Linh Bảo Thiên Tôn sáng lập.",
    "Bát Cửu Huyền Công": "Vạn kiếp bất diệt, 72 biến hóa, nhục thân thành thánh, Đạo môn chí cao hộ thể thần công.",
    "Bá Vương Tuyệt Đao": "Cửu Trọng Thiên đao pháp, đao ý cuồng bạo xé rách thương khung."
}

COSMIC_RULES_LORE = {
    "Lục Đạo Luân Hồi Chi Chủ": "Thế lực bí ẩn thao túng chư thiên nhiệm vụ, thực chất là ván cờ tranh đoạt Đạo Quả của các đại năng Bỉ Ngạn.",
    "Chân Thực Giới": "Thế giới gốc bản nguyên của vũ trụ, nơi quy tắc kiên cố nhất, các thế giới khác chỉ là hình chiếu.",
    "Bỉ Ngạn Quy Tắc": "Đứng trên dòng thời gian, hồi tố quá khứ, nhìn thấu tương lai, nắm giữ căn nguyên nhân quả."
}
