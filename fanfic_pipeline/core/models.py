"""
Data models for the Fanfic Writing Pipeline.
Defines schemas for Character Voices, POD (Point of Divergence), Relationship Dynamics,
Scene Beats, Chapters, and Critic Evaluations.
"""

from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field

class CharacterVoice(BaseModel):
    character_id: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    gender: str = "Unspecified"
    personality_core: str
    lexicon_rules: List[str] = Field(
        description="Cách xưng hô, khẩu ngữ cửa miệng, từ ngữ hay dùng hoặc cấm kỵ",
        default_factory=list
    )
    dialogue_rhythm: str = Field(description="Nhịp câu, độ dài câu, thái độ khi nói chuyện")
    micro_behaviors: List[str] = Field(
        description="Cử chỉ vô thức (ví dụ: siết chặt đao chuôi, khẽ nhếch mép, gõ ngón tay)",
        default_factory=list
    )
    moral_boundaries: str = Field(description="Ranh giới đạo đức, giới hạn không bao giờ vượt qua")
    secret_motive: Optional[str] = Field(default="", description="Động cơ ẩn sâu / Chấp niệm lớn nhất")

class RelationshipState(BaseModel):
    pair: List[str] = Field(description="Tên 2 nhân vật (ví dụ: ['Mạnh Kỳ', 'Cố Tiểu Tang'])")
    trope_type: str = Field(description="Trope quan hệ: Slow-burn, Enemies to Lovers, Hurt/Comfort, Bromance...")
    intimacy_level: int = Field(default=1, ge=1, le=10, description="Mức độ thân mật (1: Người dưng/Cảnh giác -> 10: Tri kỷ/Sinh tử tương thác)")
    current_dynamic: str = Field(description="Mô tả trạng thái tương tác hiện tại (VD: Cùng hợp tác nhưng đề phòng lẫn nhau)")
    unspoken_conflicts: List[str] = Field(default_factory=list, description="Những nút thắt tâm lý, hiểu lầm, điều chưa dám nói")

class PointOfDivergence(BaseModel):
    divergence_anchor: str = Field(description="Mốc sự kiện nguyên tác bắt đầu rẽ nhánh (VD: Nhiệm vụ Luân Hồi thứ 2 tại Ẩn Hình phường)")
    what_if_premise: str = Field(description="Giả thiết cốt lõi (VD: Có thêm thành viên thứ 6 gia nhập tiểu đội Mạnh Kỳ)")
    butterfly_effects: List[str] = Field(default_factory=list, description="Hệ quả cánh bướm tác động lên các tuyến khác")
    frozen_canon: List[str] = Field(default_factory=list, description="Những chân lý / quy tắc thế giới không bao giờ thay đổi")

class SceneBeat(BaseModel):
    beat_number: int
    scene_type: Literal["action", "dialogue", "introspection", "discovery", "emotional_climax"]
    characters_present: List[str]
    a_plot_goal: str = Field(description="Tuyến hành động / Nhiệm vụ bên ngoài (A-Plot)")
    b_plot_goal: str = Field(description="Tuyến cảm xúc / Biến chuyển tâm lý & Chemistry (B-Plot)")
    key_event: str
    tension_element: str

class ChapterOutline(BaseModel):
    chapter_number: int
    title: str
    point_of_view: str = Field(description="Góc nhìn nhân vật (POV)")
    core_conflict: str
    scene_beats: List[SceneBeat]
    foreshadowing_hooks: List[str] = Field(default_factory=list, description="Phục bút cài cắm trong chương")

class OOCCriticResult(BaseModel):
    has_ooc: bool
    ooc_score: int = Field(ge=0, le=10, description="10 là hoàn toàn In-Character, dưới 7 là OOC")
    critiques: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Danh sách phát hiện câu thoại/hành vi bị OOC kèm gợi ý sửa"
    )
    canon_consistency_score: int = Field(ge=0, le=10)
    de_ai_score: int = Field(ge=0, le=10, description="Đánh giá mức độ tự nhiên, không bị sáo rỗng AI")
    overall_verdict: Literal["PASS", "REVISE", "REJECT"]
    actionable_revision_prompt: Optional[str] = None

class ChapterDraft(BaseModel):
    chapter_number: int
    title: str
    word_count: int
    content: str
    summary: str
    state_updates: Dict[str, Any] = Field(default_factory=dict)
