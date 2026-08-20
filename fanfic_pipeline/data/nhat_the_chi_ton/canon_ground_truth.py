"""
Bilingual (Vietnamese + Chinese) Ground Truth Lore for 'Nhất Thế Chi Tôn' (一世之尊).
Enables zero-hallucination FTS search across 1409 Chinese EPUB chapters.
"""
from typing import Dict, List, Any

# Factions: Canonical VN Name -> (Chinese Search Keys, Description)
FACTIONS_GROUND_TRUTH: Dict[str, Dict[str, Any]] = {
    "Thiếu Lâm Tự": {"cn": ["少林寺", "少林"], "type": "Chính Đạo", "desc": "A Di Đà Phật / Như Lai truyền thừa, đệ nhất Phật môn"},
    "Tẩy Kiếm Các": {"cn": ["洗剑阁"], "type": "Chính Đạo", "desc": "Tô Vô Danh, Giang Chỉ Vi - Trảm Đoạn Chấp Niệm, Kiếm Xuất Vô Hối"},
    "Chân Võ Tông": {"cn": ["真武宗", "真武派"], "type": "Chính Đạo", "desc": "Trương Tam Phong / Đạo Đức Thiên Tôn truyền thừa"},
    "Huyền Thiên Tông": {"cn": ["玄天宗"], "type": "Chính Đạo", "desc": "Thiên Đế truyền thừa, chấp chưởng Thời Gian Chi Đao"},
    "Ngọc Hư Cung": {"cn": ["玉虚宫", "昆仑山玉虚宫"], "type": "Chính Đạo", "desc": "Nguyên Thủy Thiên Tôn chí cao đạo tràng"},
    "Lang Nha Nguyễn Thị": {"cn": ["琅琊阮氏", "阮氏"], "type": "Thế Gia", "desc": "Nguyễn Ngọc Thư - Cầm Đạo Âm Luật Thế Gia"},
    "Hoàng Cơ Thần Triều": {"cn": ["皇极神朝", "大晋皇室"], "type": "Hoàng Triều", "desc": "Triệu Hằng - Hoàng Long Ngọc Tỷ"},
    "Tố Nữ Đạo": {"cn": ["素女道"], "type": "Ma Môn", "desc": "Cố Tiểu Tang, Vô Sinh Lão Mẫu - Cửu Thiên Huyền Nữ / Hoan Hỷ bí thuật"},
    "Diệt Thiên Môn": {"cn": ["灭天门"], "type": "Ma Môn", "desc": "Lục Đạo Ma Quân - Diệt Thiên Ma Đao sát phạt"},
    "Hoan Hỷ Thiền": {"cn": ["欢喜禅", "欢喜庙"], "type": "Ma Môn", "desc": "Tà Thiền bí thuật, âm dương thải bổ"},
    "Bất Tử Yêu Đạo": {"cn": ["不死妖道", "妖圣"], "type": "Ma Môn", "desc": "Yêu Tộc tàn hồn truyền thừa"},
    "Tu La Đạo": {"cn": ["修罗道", "阿修罗"], "type": "Ma Môn", "desc": "Huyết sát ma công"},
    "Huyết Hải Giáo": {"cn": ["血海教", "幽冥血海"], "type": "Ma Môn", "desc": "U Minh Huyết Hải truyền thừa"}
}

# Martial Arts & Divine Techniques: Canonical VN Name -> (Chinese Search Keys, Description)
DIVINE_MARTIAL_ARTS: Dict[str, Dict[str, Any]] = {
    "Như Lai Thần Chưởng": {"cn": ["如来神掌"], "tier": "Bỉ Ngạn", "desc": "Cửu thức thần chưởng trấn áp vạn giới, do Phật Tổ sáng lập"},
    "Tiệt Thiên Thất Kiếm": {"cn": ["截天七剑"], "tier": "Bỉ Ngạn", "desc": "Thất thức kiếm ý trảm đoạn quy tắc đại đạo, do Linh Bảo Thiên Tôn sáng lập"},
    "Bát Cửu Huyền Công": {"cn": ["八九玄功"], "tier": "Bỉ Ngạn", "desc": "Vạn kiếp bất diệt, 72 biến hóa, Nguyên Thủy Thiên Tôn hộ thể thần công"},
    "Nhất Khí Hóa Tam Thanh": {"cn": ["一气化三清"], "tier": "Bỉ Ngạn", "desc": "Đạo Đức Thiên Tôn chí cao thần thông"},
    "Bá Vương Tuyệt Đao": {"cn": ["霸王绝刀", "霸王六斩"], "tier": "Pháp Thân/Bỉ Ngạn", "desc": "Cửu Trọng Thiên Bá Vương đao pháp cuồng bạo"},
    "A Nan Phá Giới Đao Pháp": {"cn": ["阿难破戒刀", "破戒刀法", "断清净"], "tier": "Pháp Thân", "desc": "Ma Phật An Nan tuyệt kỹ: Đoạn Thanh Ty, Lạc Hồng Trần"},
    "Kim Cương Bất Hoại Thần Công": {"cn": ["金刚不坏神功", "金刚不坏"], "tier": "Ngoại Cảnh", "desc": "Thiếu Lâm Tự 72 tuyệt kỹ đỉnh phong"},
    "Dịch Cân Kinh": {"cn": ["易筋经"], "tier": "Ngoại Cảnh/Pháp Thân", "desc": "Thiếu Lâm Tự trấn tự chân kinh"},
    "Thiên Ma Công": {"cn": ["天魔功", "天魔四蚀"], "tier": "Pháp Thân", "desc": "Lục Đại Ma Môn chí cao ma công"},
    "Tố Nữ Thiên Ma Thập Bát Thức": {"cn": ["天魔十八式", "素女天魔"], "tier": "Ngoại Cảnh", "desc": "Tố Nữ Đạo ám sát cùng mị thuật thân pháp"},
    "Diệt Thiên Ma Đao": {"cn": ["灭天魔刀"], "tier": "Pháp Thân", "desc": "Diệt Thiên Môn sát phạt thần đao"},
    "Thần Tiêu Lôi Pháp": {"cn": ["神霄雷法", "神霄九灭"], "tier": "Pháp Thân", "desc": "Cửu Thiên Huyền Lôi chính tông"},
    "Thái Cực Thần Công": {"cn": ["太极神功", "太极拳", "太极剑"], "tier": "Pháp Thân", "desc": "Chân Võ Tông Trương Tam Phong sáng lập"},
    "Lạc Thư Bát Quái": {"cn": ["洛书", "八卦", "易数"], "tier": "Thần Thông", "desc": "Tiên thiên suy diễn thiên cơ nhân quả"},
    "Tử Vi Đẩu Số": {"cn": ["紫微斗数"], "tier": "Thần Thông", "desc": "Hoàng triều bí truyền chiêm tinh chi thuật"},
    "Phượng Tê Cầm Phổ": {"cn": ["凤栖琴", "龙吟琴"], "tier": "Thần Binh/Thần Thông", "desc": "Lang Nha Nguyễn Thị tuyệt thế âm luật"},
    "Ngũ Lôi Hóa Cực Thủ": {"cn": ["五雷化极手", "五雷掌"], "tier": "Ngoại Cảnh", "desc": "Lôi điện sát phạt bí thuật"},
    "Hóa Huyết Thần Đao": {"cn": ["化血神刀"], "tier": "Ngoại Cảnh/Pháp Thân", "desc": "Huyết Hải Giáo sát phạt thần đao"}
}

# Realms: Canonical VN Name -> Chinese Search Keys
REALM_CN_MAP = {
    "Bách Nhật Trúc Cơ": ["百日筑基"],
    "Súc Khí (Thiền Định Súc Khí)": ["蓄气", "禅定蓄气"],
    "Khai Khiếu (Sơ kỳ - 1-4 Khiếu)": ["开窍"],
    "Khai Khiếu (Trung kỳ - 5-7 Khiếu)": ["开窍", "九窍"],
    "Khai Khiếu (Hậu kỳ - 8-9 Khiếu)": ["九窍齐开"],
    "Khai Khiếu (Cửu Khiếu Tề Khai - Viên Mãn)": ["天人交感", "九窍圆满"],
    "Bán Bộ Ngoại Cảnh (Thiên Nhân Hợp Nhất)": ["半步外景", "天人合一", "天人化生"],
    "Ngoại Cảnh (Nhất Trọng Thiên)": ["外景", "一重天"],
    "Ngoại Cảnh (Nhị Trọng Thiên)": ["二重天"],
    "Ngoại Cảnh (Tam Trọng Thiên)": ["三重天"],
    "Ngoại Cảnh (Tứ Trọng Thiên)": ["四重天"],
    "Ngoại Cảnh (Ngũ Trọng Thiên)": ["五重天"],
    "Ngoại Cảnh (Lục Trọng Thiên)": ["六重天"],
    "Ngoại Cảnh (Thất Trọng Thiên - Tông Sư)": ["七重天", "宗师"],
    "Ngoại Cảnh (Bát Trọng Thiên - Đại Tông Sư)": ["八重天", "大宗师"],
    "Ngoại Cảnh (Cửu Trọng Thiên - Đỉnh Phong)": ["九重天", "外景巅峰"],
    "Bán Bộ Pháp Thân": ["半步法身"],
    "Pháp Thân (Nhân Tiên)": ["法身", "人仙"],
    "Pháp Thân (Địa Tiên)": ["地仙"],
    "Pháp Thân (Thiên Tiên)": ["天仙"],
    "Bán Bộ Truyền Thuyết": ["半步传说"],
    "Truyền Thuyết Cảnh": ["传说"],
    "Tạo Hóa Cảnh": ["造化"],
    "Bán Bộ Bỉ Ngạn": ["半步彼岸"],
    "Bỉ Ngạn Cảnh": ["彼岸"],
    "Đạo Quả (Siêu Thoát)": ["道果", "道果雏形"]
}
