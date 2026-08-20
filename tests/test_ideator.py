import pytest, tempfile, os
from fanfic_pipeline.core.ideator import PremiseIdeator, OCCreator
from fanfic_pipeline.core.state_manager import ProjectStateManager
from fanfic_pipeline.core.models import PointOfDivergence

def test_premise_ideator_returns_options():
    premises = PremiseIdeator.brainstorm(fandom="Nhất Thế Chi Tôn", trope_hint="Xuyên không")
    assert len(premises) >= 3
    assert all(isinstance(p, PointOfDivergence) for p in premises)
    assert premises[0].divergence_anchor != ""
    assert premises[0].what_if_premise != ""

def test_oc_creator_crafts_complete_voice():
    voice, rel = OCCreator.craft_oc(
        character_name="Lục Thanh Tiêu",
        concept="Đao khách cơ quan thuật",
        role="Thành viên thứ 6"
    )
    assert voice.name == "Lục Thanh Tiêu"
    assert len(voice.micro_behaviors) >= 1
    assert voice.dialogue_rhythm != ""
    assert rel.pair == ["Lục Thanh Tiêu", "Mạnh Kỳ"]
    assert rel.intimacy_level >= 1
