from typing import Dict, Any, List
from pydantic import BaseModel

class VoiceDynamics(BaseModel):
    character: str
    intimacy_with: str
    intimacy_level: int = 1
    combat_tone: str = ""
    banter_tone: str = ""
    address_form: str = ""

DEFAULT_VOICE_DYNAMICS = {
    ("Mạnh Kỳ", "Giang Chỉ Vi"): VoiceDynamics(
        character="Mạnh Kỳ", intimacy_with="Giang Chỉ Vi", intimacy_level=5,
        combat_tone="Đao kiếm phối hợp ăn ý, tin tưởng tuyệt đối sau lưng cho đối phương.",
        banter_tone="Thoải mái xưng hô Giang cô nương / Chỉ Vi, thích giả bộ cao nhân nhưng hay bị bóc mẽ.",
        address_form="Giang cô nương -> Chỉ Vi"
    ),
    ("Mạnh Kỳ", "Cố Tiểu Tang"): VoiceDynamics(
        character="Mạnh Kỳ", intimacy_with="Cố Tiểu Tang", intimacy_level=3,
        combat_tone="Cực kỳ cảnh giác, đề phòng bẫy rập và mị hoặc.",
        banter_tone="Đấu trí gay gắt, mỉa mai gọi Yêu nữ, vừa đề phòng vừa khó cưỡng lại.",
        address_form="Yêu nữ / Tiểu Tang"
    ),
    ("Mạnh Kỳ", "Tề Chính Ngôn"): VoiceDynamics(
        character="Mạnh Kỳ", intimacy_with="Tề Chính Ngôn", intimacy_level=6,
        combat_tone="Ăn ý trầm tĩnh, bọc lót chắc chắn.",
        banter_tone="Gọi Tề sư huynh / Mặt đơ, tin cậy chân thành như huynh đệ vào sinh ra tử.",
        address_form="Tề sư huynh"
    ),
    ("Mạnh Kỳ", "Nguyễn Ngọc Thư"): VoiceDynamics(
        character="Mạnh Kỳ", intimacy_with="Nguyễn Ngọc Thư", intimacy_level=5,
        combat_tone="Bảo vệ chủ công cầm sư, dùng đao phong che chắn tầm bắn âm ba.",
        banter_tone="Trêu chọc thói mê ăn vặt cá khô/bánh ngọt của nàng; nàng kiêu kỳ đỏ mặt đáp lại lạnh lùng.",
        address_form="Nguyễn cô nương / Ngọc Thư"
    )
}


def get_voice_dynamics(char1: str, char2: str, intimacy_level: int = 5) -> VoiceDynamics:
    for pair in [(char1, char2), (char2, char1)]:
        if pair in DEFAULT_VOICE_DYNAMICS:
            vd = DEFAULT_VOICE_DYNAMICS[pair].model_copy()
            vd.intimacy_level = intimacy_level
            return vd
    return VoiceDynamics(character=char1, intimacy_with=char2, intimacy_level=intimacy_level, combat_tone="Nghiêm túc", banter_tone="Tự nhiên", address_form="Bình thường")
