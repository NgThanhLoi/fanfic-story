from typing import Dict, Any, List

TONE_PROMPTS = {
    "combat": "Văn phong dồn dập, đao phong kiếm khí lẫm liệt, câu ngắn gọn, tập trung vào chiêu thức và phản xạ sống còn.",
    "banter": "Văn phong dí dỏm, đối thoại tự nhiên, có sự trêu đùa và cà khịa nhưng giữ đúng khí chất hiệp khách.",
    "cultivation": "Văn phong sâu lắng, huyền diệu, miêu tả cảm ngộ thiên địa, tuần hoàn chân khí và biến chuyển linh hồn.",
    "deduction": "Văn phong chặt chẽ, tư duy sắc bén, xâu chuỗi manh mối logic, chú ý quan sát từng chi tiết nhỏ.",
    "suspense": "Không khí căng thẳng, dồn dập, cảm giác nguy cơ cận kề, bước đi cẩn trọng.",
    "emotional": "Lắng đọng, giàu sức gợi, tập trung vào ánh mắt và chuyển biến nội tâm sâu kín."
}

def get_dynamic_style_contract(scene_mode: str, active_characters: List[str] = None, intimacy_levels: Dict[str, int] = None) -> str:
    base_tone = TONE_PROMPTS.get(scene_mode, TONE_PROMPTS["combat"])
    return f"[PHONG CÁCH PHÂN CẢNH ({scene_mode.upper()})]: {base_tone}\n- Nguyên tắc: SHOW, DON'T TELL (Thể hiện qua hành động và đối thoại)."
