"""
P1.10 — Canon Intelligence Engine 2.0: 4-Pillar Deep Comprehension for 1409 Chapters.
Pillars:
1. TimelineState: Dynamic state snapshot at chapter T
2. PlotConspiracyGraph: 12 Grand Arcs with masterminds & conspiracies
3. DynamicVoiceArc: Multi-stage psychological and voice progression
4. EpistemicHorizon: Time-locked forbidden/known facts to prevent omniscient AI
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fanfic_pipeline.core.models import CharacterVoice

# ---------------------------------------------------------------------------
# PILLAR 2: 12 Grand Arcs & Plot Conspiracies
# ---------------------------------------------------------------------------
GRAND_ARCS = [
    {
        "arc_id": "arc_01",
        "title": "Tân Thủ Luân Hồi & Thiếu Lâm Tàng Kinh Các",
        "start_ch": 1, "end_ch": 50,
        "mastermind": "Ma Phật An Nan (Ẩn thân sau Lục Đạo)",
        "conspiracy": "Gài bẫy truyền thừa A Nan Phá Giới Đao và Lôi Đao cho Mạnh Kỳ để làm đạo tiêu trùng sinh.",
        "invariants": ["Mạnh Kỳ vào Thiếu Lâm Tự", "Ẩn Hình Phường đụng độ Đoạt Mệnh Kiếm", "Kết bạn Chỉ Vi, Chính Ngôn, Ngọc Thư"]
    },
    {
        "arc_id": "arc_02",
        "title": "Giang Hồ Sơ Xuất & Nhân Bảng Tranh Phong",
        "start_ch": 51, "end_ch": 150,
        "mastermind": "Lục Đạo Luân Hồi & Lục Đại Ma Môn",
        "conspiracy": "Cố Tiểu Tang dùng thân phận Yêu Nữ tiếp cận Mạnh Kỳ, dò xét bố cục của Vô Sinh Lão Mẫu.",
        "invariants": ["Đoạt danh hiệu Cuồng Đao Tô Mạnh", "Huyễn Hình Đại Pháp của Đoạn Hướng Phi", "Gia nhập Lục Phiến Môn"]
    },
    {
        "arc_id": "arc_03",
        "title": "Cửu Trọng Thiên Di Tích & Đao Phách Cửu Lôi",
        "start_ch": 151, "end_ch": 300,
        "mastermind": "Thiên Đế & Lôi Thần tàn hồn",
        "conspiracy": "Tranh đoạt Lôi Trữ Cửu Vị, thức tỉnh Chân Võ tàn thiên.",
        "invariants": ["Mạnh Kỳ đạt Khai Khiếu Cửu Khiếu Tề Khai", "Bá Vương Tuyệt Đao nhận chủ sơ bộ", "Tề Chính Ngôn tiếp nhận Ma Hoàng truyền thừa"]
    },
    {
        "arc_id": "arc_04",
        "title": "Đại Biến Thiếu Lâm & Chém Đứt Dây Rối",
        "start_ch": 301, "end_ch": 500,
        "mastermind": "Ma Phật An Nan & Huyền Bi hòa thượng",
        "conspiracy": "Thân thế Tô Tử Viễn bại lộ, Thiếu Lâm thanh trừng phản đồ, thoát ly Thiếu Lâm hoàn tục.",
        "invariants": ["Đột phá Ngoại Cảnh Thiên Nhân Hợp Nhất", "Chỉ Vi ngộ Tiệt Thiên Thất Kiếm", "Mạnh Kỳ chặt đứt chấp niệm Thiếu Lâm"]
    },
    {
        "arc_id": "arc_05",
        "title": "Tô Tiên Sinh Tóc Bạc & Trầm Luân Khổ Hải",
        "start_ch": 501, "end_ch": 800,
        "mastermind": "Kim Mẫu / Vô Sinh Lão Mẫu",
        "conspiracy": "Cố Tiểu Tang tự sát tại Thiếu Lâm để đoạn tuyệt khống chế của Kim Mẫu; Mạnh Kỳ tóc bạc 10 năm ôm hận.",
        "invariants": ["Tiểu Tang chết trước mặt Mạnh Kỳ", "Mạnh Kỳ hóa thân Tô Tiên sinh quán trà", "Đột phá Ngoại Cảnh Đỉnh Phong Tông Sư"]
    },
    {
        "arc_id": "arc_06",
        "title": "Chứng Đạo Pháp Thân & Khai Thiên Tích Địa",
        "start_ch": 801, "end_ch": 1100,
        "mastermind": "Nguyên Thủy Thiên Tôn & Đạo Đức Thiên Tôn",
        "conspiracy": "Mạnh Kỳ chứng Bất Diệt Nguyên Thủy Pháp Thân, tiếp nhận nhân quả Côn Luân Ngọc Hư Cung.",
        "invariants": ["Chứng đắc Pháp Thân Nhân Tiên -> Địa Tiên", "Phục sinh Cố Tiểu Tang", "Tề Chính Ngôn lập Ma Đạo giải phóng phàm nhân"]
    },
    {
        "arc_id": "arc_07",
        "title": "Đại Kiếp Mạt Thế & Bỉ Ngạn Tranh Đạo Quả",
        "start_ch": 1101, "end_ch": 1409,
        "mastermind": "Tam Thanh, Ma Phật, A Di Đà Phật, Kim Mẫu",
        "conspiracy": "Đại kiếp mạt kiếp hủy diệt kỷ nguyên, chư thiên Bỉ Ngạn quy vị tranh đoạt Đạo Quả duy nhất.",
        "invariants": ["Mạnh Kỳ đăng lâm Bỉ Ngạn", "Chém giết Ma Phật An Nan", "Đạo Quả siêu thoát viên mãn"]
    }
]

# ---------------------------------------------------------------------------
# PILLAR 3: Dynamic Multi-Stage Voice Progression
# ---------------------------------------------------------------------------
STAGE_VOICES: Dict[str, List[Dict[str, Any]]] = {
    "meng_qi": [
        {
            "max_ch": 50,
            "title": "Chân Định (Tiểu Hòa Thượng)",
            "realm": "Bách Nhật Trúc Cơ -> Khai Khiếu (4 khiếu)",
            "personality": "Sợ chết, lươn lẹo, thích 'trang bức', miệng xưng 'Bần tăng' nhưng lòng hướng hồng trần.",
            "rhythm": "Nhanh, dí dỏm, biến hóa, hay tự khen mình anh tuấn tiêu sái.",
            "micro": ["Vô thức xoa đầu trọc", "Mắt đảo quanh tìm đường chuồn"]
        },
        {
            "max_ch": 200,
            "title": "Cuồng Đao Tô Mạnh (Nhân Bảng Thiên Kiêu)",
            "realm": "Khai Khiếu (Cửu Khiếu Tề Khai) -> Bán Bộ Ngoại Cảnh",
            "personality": "Hào sảng, ngạo khí, trọng tình trọng nghĩa, đao ý cuồng bạo bất khuất.",
            "rhythm": "Dứt khoát, đanh thép, tiếng cười vang rền, trêu chọc Cố Tiểu Tang.",
            "micro": ["Tay phải miết chặt chuôi Lôi Đao", "Khóe miệng nhếch lên nụ cười tự tin"]
        },
        {
            "max_ch": 600,
            "title": "Tô Tiên Sinh (Tóc Bạc Tang Thương)",
            "realm": "Ngoại Cảnh (Thất Trọng Thiên - Tông Sư)",
            "personality": "Lãnh đạm, trầm mặc, đôi mắt tang thương như tro tàn, mang chấp niệm báo thù sâu sắc.",
            "rhythm": "Chậm rãi, ít lời, giọng khàn khàn trầm thấp, không còn đùa cợt.",
            "micro": ["Gió thổi bay lọn tóc bạc trước trán", "Ngắm nhìn trâm cài ngọc lưu ly của Tiểu Tang"]
        },
        {
            "max_ch": 1409,
            "title": "Ngọc Hư Chưởng Giáo / Nguyên Thủy Tô Mạnh",
            "realm": "Pháp Thân -> Bỉ Ngạn",
            "personality": "Uy nghiêm, thấu triệt nhân quả chư thiên, đại đạo chí giản, chấp chưởng Côn Luân.",
            "rhythm": "Uy nghiêm, bao la như thiên địa, lời ra như pháp chỉ.",
            "micro": ["Ống tay áo bào tung bay như cuốn theo vạn giới", "Ánh mắt phản chiếu dòng sông thời gian"]
        }
    ]
}

# ---------------------------------------------------------------------------
# CANON INTELLIGENCE ENGINE
# ---------------------------------------------------------------------------
class CanonIntelligenceEngine:
    @classmethod
    def get_arc_for_chapter(cls, ch: int) -> Dict[str, Any]:
        for arc in GRAND_ARCS:
            if arc["start_ch"] <= ch <= arc["end_ch"]:
                return arc
        return GRAND_ARCS[-1]

    @classmethod
    def get_voice_for_chapter(cls, char_name: str, ch: int, base_voice: CharacterVoice) -> CharacterVoice:
        cid = char_name.lower().replace(" ", "_")
        if hasattr(base_voice, "character_id") and base_voice.character_id:
            cid = base_voice.character_id.lower()
        if "mạnh" in cid or "manh" in cid: cid = "meng_qi"
        elif "chỉ" in cid or "chi" in cid: cid = "jiang_zhiwei"
        elif "tang" in cid: cid = "gu_xiaosang"

        stages = STAGE_VOICES.get(cid, [])
        for stage in stages:
            if ch <= stage["max_ch"]:
                v = base_voice.model_copy()
                v.personality_core = f"[{stage['title']}] {stage['personality']}"
                v.dialogue_rhythm = stage["rhythm"]
                v.micro_behaviors = stage["micro"] + v.micro_behaviors[:2]
                return v
        return base_voice


    @classmethod
    def get_epistemic_boundary(cls, char_name: str, ch: int) -> Dict[str, List[str]]:
        """Strict time-locked forbidden knowledge preventing omniscient AI leaks."""
        forbidden = []
        known = []
        if "meng_qi" in char_name.lower() or "mạnh kỳ" in char_name.lower():
            if ch < 500:
                forbidden.extend([
                    "Ma Phật An Nan chính là Lục Đạo Luân Hồi Chi Chủ chủ mưu",
                    "Cố Tiểu Tang là hóa thân/đạo tiêu của Vô Sinh Lão Mẫu",
                    "Thân phận Bỉ Ngạn của Tam Thanh và Nguyên Thủy Thiên Tôn"
                ])
                known.append("Lục Đạo là thế lực bí ẩn phát thưởng Thiện Công")
            if ch < 150:
                forbidden.append("Tề Chính Ngôn bí mật tu luyện Ma Hoàng truyền thừa")
                known.append("Tề Chính Ngôn là sư huynh mặt đơ, tin cậy tuyệt đối")
        return {"forbidden": forbidden, "known": known}

    @classmethod
    def get_timeline_snapshot(cls, ch: int) -> Dict[str, Any]:
        arc = cls.get_arc_for_chapter(ch)
        return {
            "current_chapter": ch,
            "active_grand_arc": arc["title"],
            "mastermind_shadow": arc["mastermind"],
            "underlying_conspiracy": arc["conspiracy"],
            "historical_invariants": arc["invariants"]
        }
