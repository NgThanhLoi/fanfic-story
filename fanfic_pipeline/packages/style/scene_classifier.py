from typing import List, Dict

SCENE_KEYWORDS = {
    "combat": ["đao", "kiếm", "sát", "quyết đấu", "chém", "xuất thủ", "chưởng phong", "huyệt vị", "đột kích", "giao thủ"],
    "banter": ["cười", "trêu", "ha ha", "khóe miệng", "tiểu tử", "cà khịa", "chế giễu", "uống rượu"],
    "cultivation": ["đột phá", "kinh mạch", "khai khiếu", "chân khí", "tĩnh tọa", "linh khí", "đả tọa", "bế quan"],
    "deduction": ["manh mối", "suy đoán", "chân tướng", "hung thủ", "nghi vấn", "bí mật", "ẩn tình"],
    "suspense": ["hắc y nhân", "rình rập", "nguy hiểm", "sát khí", "âm u", "bất ngờ", "phục kích"],
    "emotional": ["thở dài", "nhìn nhau", "trầm mặc", "bi thương", "ly biệt", "ánh mắt", "xao xuyến"]
}

def classify_scene(author_instruction: str, outline_topic: str = "", recent_text: str = "") -> str:
    combined = f"{author_instruction} {outline_topic} {recent_text}".lower()
    scores = {mode: sum(1 for kw in kw_list if kw in combined) for mode, kw_list in SCENE_KEYWORDS.items()}
    best_mode = max(scores, key=scores.get)
    return best_mode if scores[best_mode] > 0 else "banter"

