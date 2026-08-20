"""
P5.4 — Ideation Module: Premise Generator & OC (Original Character) Crafter.
Supports both Live LLM reasoning and structured domain fallbacks.
"""
import os, json, re
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from fanfic_pipeline.core.models import PointOfDivergence, CharacterVoice, RelationshipState
from fanfic_pipeline.core.model_router import PipelineModelRouter, AgentModelConfig, LLMInvoker

class PremiseIdeator:
    @classmethod
    def brainstorm(
        cls,
        fandom: str = "Nhất Thế Chi Tôn",
        trope_hint: str = "Hệ thống / Xuyên không / Thêm thành viên",
        router: Optional[PipelineModelRouter] = None
    ) -> List[PointOfDivergence]:
        prompt = f"""Bạn là Tổng Biên Tập Đồng Nhân Đỉnh Cao.
Hãy gợi ý 3 Ý TƯỞNG RẼ NHÁNH (Point of Divergence - POD) độc đáo, cuốn hút cho tác phẩm [{fandom}] dựa trên chủ đề gợi ý: "{trope_hint}".

Trả về JSON danh sách 3 objects với đúng schema:
[
  {{
    "divergence_anchor": "Mốc rẽ nhánh (VD: Chương 5 tại Thiếu Lâm / Nhiệm vụ Ẩn Hình phường)",
    "what_if_premise": "Giả thiết cốt lõi (VD: Nhân vật chính thức tỉnh được ký ức tiền kiếp sớm hơn)",
    "butterfly_effects": ["Hiệu quả 1 tác động lên Cố Tiểu Tang", "Hiệu quả 2 tác động lên thế cục Luân Hồi"],
    "frozen_canon": ["Quy tắc Lục Đạo không đổi", "Phân cấp 26 cảnh giới tu vi không đổi"]
  }}
]
Chỉ xuất ra JSON hợp lệ.
"""
        cfg = router.architect_agent if router else AgentModelConfig(
            provider="cliproxyapi",
            model_name="deepseek-v4-flash-free",
            base_url="http://47.237.140.200/v1",
            api_key_env="cpa-local-9f3a7e2b1c4d"
        )
        api_key = os.environ.get("CLIPROXY_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            try:
                res = LLMInvoker.call_agent_llm(cfg, "You are a creative fanfic architect. Output JSON only.", prompt, json_mode=True)
                json_str = res
                if "```json" in res:
                    json_str = res.split("```json")[1].split("```")[0].strip()
                elif "```" in res:
                    json_str = res.split("```")[1].split("```")[0].strip()
                data = json.loads(json_str)
                if isinstance(data, list):
                    return [PointOfDivergence(**d) for d in data]
                elif isinstance(data, dict) and "premises" in data:
                    return [PointOfDivergence(**d) for d in data["premises"]]
            except Exception:
                pass

        # Domain Fallback
        return [
            PointOfDivergence(
                divergence_anchor="Nhiệm vụ Luân Hồi tân thủ (Ẩn Hình Phường)",
                what_if_premise=f"Tuyến [{trope_hint}]: Mạnh Kỳ thức tỉnh đao hồn Lôi Đao sớm 3 năm, nhận ra dấu vết Ma Phật ngay từ lần chạm mặt Cố Tiểu Tang đầu tiên.",
                butterfly_effects=["Tiểu Tang sinh lòng hiếu kỳ cực độ, chủ động liên thủ bí mật", "Tiểu đội Luân Hồi sớm chuẩn bị công pháp phòng ngự linh hồn"],
                frozen_canon=["Quy tắc Luân Hồi Chi Chủ không đổi", "Cảnh giới 26 tầng tu vi giữ nguyên"]
            ),
            PointOfDivergence(
                divergence_anchor="Thiếu Lâm Tự Tàng Kinh Các (Chương 1-5)",
                what_if_premise=f"Tuyến [{trope_hint}]: Xuất hiện thành viên thứ 6 gia nhập nhóm Luân Hồi, mang theo một phần bí mật của Cửu Trọng Thiên cổ đại.",
                butterfly_effects=["Nhiệm vụ Luân Hồi nâng độ khó lên mức Địa ngục", "Lục Đạo Luân Hồi Chi Chủ bắt đầu để mắt sát sao"],
                frozen_canon=["Bản chất Ma Phật An Nan không đổi", "Thế giới quan Tam Giới giữ nguyên"]
            ),
            PointOfDivergence(
                divergence_anchor="Đại hội Trích Tinh (Trước khi rời Thiếu Lâm)",
                what_if_premise=f"Tuyến [{trope_hint}]: Giang Chỉ Vi cùng Mạnh Kỳ cùng nhau kích hoạt Tiệt Thiên Thất Kiếm tàn thiên, mở ra lối tu luyện Song Kiếm Hợp Bích.",
                butterfly_effects=["Kiếm tâm của Giang Chỉ Vi đột phá trước thời hạn", "Tố Nữ Đạo coi tiểu đội là mục tiêu thanh trừng số 1"],
                frozen_canon=["Cửu Kiếm Quy Nhất chân lý không đổi", "Thân thế Huyền Giới giữ nguyên"]
            )
        ]


class OCCreator:
    @classmethod
    def craft_oc(
        cls,
        character_name: str,
        concept: str,
        role: str = "Thành viên tiểu đội Luân Hồi",
        router: Optional[PipelineModelRouter] = None
    ) -> Tuple[CharacterVoice, RelationshipState]:
        prompt = f"""Bạn là Chuyên Gia Thiết Kế Nhân Vật Đồng Nhân (OC Character Designer).
Hãy tạo thiết lập nhân vật gốc (OC) [{character_name}] cho fanfic Nhất Thế Chi Tôn:
- Ý tưởng cốt lõi: {concept}
- Vai trò: {role}

Trả về JSON đúng cấu trúc:
{{
  "character_id": "{character_name.lower().replace(' ', '_')}",
  "name": "{character_name}",
  "aliases": ["Biệt hiệu 1", "Biệt hiệu 2"],
  "gender": "Nam/Nữ",
  "personality_core": "Mô tả tính cách cốt lõi 1-2 câu",
  "lexicon_rules": ["Khẩu ngữ cửa miệng", "Cách xưng hô với Mạnh Kỳ/Chỉ Vi"],
  "dialogue_rhythm": "Nhịp câu, độ dài, phong thái khi nói",
  "micro_behaviors": ["Thói quen vi mô 1", "Thói quen vi mô 2"],
  "moral_boundaries": "Giới hạn đạo đức không bao giờ vượt qua",
  "secret_motive": "Động cơ ẩn sâu / Chấp niệm lớn nhất",
  "relationship_with_mc": {{
    "trope_type": "Comrades in Arms / Rivalry / Slow-burn",
    "intimacy_level": 3,
    "current_dynamic": "Mô tả tương tác hiện tại với Mạnh Kỳ",
    "unspoken_conflicts": ["Xung đột tiềm ẩn hoặc bí mật chưa thổ lộ"]
  }}
}}
Chỉ xuất ra JSON hợp lệ.
"""
        cfg = router.architect_agent if router else AgentModelConfig(
            provider="cliproxyapi",
            model_name="deepseek-v4-flash-free",
            base_url="http://47.237.140.200/v1",
            api_key_env="cpa-local-9f3a7e2b1c4d"
        )
        api_key = os.environ.get("CLIPROXY_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            try:
                res = LLMInvoker.call_agent_llm(cfg, "You are a character design master. Output JSON only.", prompt, json_mode=True)
                json_str = res
                if "```json" in res:
                    json_str = res.split("```json")[1].split("```")[0].strip()
                elif "```" in res:
                    json_str = res.split("```")[1].split("```")[0].strip()
                data = json.loads(json_str)
                rel_data = data.pop("relationship_with_mc", {})
                voice = CharacterVoice(**data)
                rel = RelationshipState(
                    pair=[character_name, "Mạnh Kỳ"],
                    trope_type=rel_data.get("trope_type", "Comrades in Arms"),
                    intimacy_level=rel_data.get("intimacy_level", 3),
                    current_dynamic=rel_data.get("current_dynamic", "Đồng đội mới gia nhập, cùng kề vai chiến đấu"),
                    unspoken_conflicts=rel_data.get("unspoken_conflicts", [])
                )
                return voice, rel
            except Exception:
                pass

        # Fallback
        voice = CharacterVoice(
            character_id=character_name.lower().replace(" ", "_"),
            name=character_name,
            aliases=[f"{character_name} Đao Khách", "Tiểu Hữu"],
            gender="Nam",
            personality_core=f"Ngoại biểu phóng khoáng nhưng nội tâm cẩn mật, am hiểu cơ quan thuật và kỳ môn độn giáp ({concept}).",
            lexicon_rules=["Xưng 'tại hạ/tôi', gọi Mạnh Kỳ là 'Tô huynh/Mạnh huynh'", "Thường chêm câu 'Việc này có điều kỳ quái'"],
            dialogue_rhythm="Dứt khoát, logic, hay phân tích tình huống trước khi ra tay.",
            micro_behaviors=["Xoay nhẹ chiếc nhẫn ngọc ở ngón trỏ khi suy nghĩ", "Luôn chọn vị trí đứng gần cửa thoát hiểm"],
            moral_boundaries="Tuyệt đối không đâm sau lưng đồng đội trong Luân Hồi.",
            secret_motive="Tìm kiếm tung tích sư môn đã biến mất trong một nhiệm vụ Luân Hồi cổ đại."
        )
        rel = RelationshipState(
            pair=[character_name, "Mạnh Kỳ"],
            trope_type="Comrades in Arms / Mutual Trust",
            intimacy_level=3,
            current_dynamic="Đồng đội ăn ý, hỗ trợ bọc lót chiến thuật cho Lôi Đao của Mạnh Kỳ",
            unspoken_conflicts=["Che giấu thân phận thật sự về truyền thừa bí mật"]
        )
        return voice, rel
