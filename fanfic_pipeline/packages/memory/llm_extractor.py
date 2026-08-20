"""
P4.1 — LLM State Extractor (JSON schema + evidence-substring invariant):
- LLM đề xuất StateDelta với JSON schema, evidence phải là substring của draft
- Regex validator chéo (giữ nguyên BUG-06 invariant)
"""
import json, re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

STATEDELTA_SCHEMA = {
    "type": "object",
    "required": ["chapter_number", "evidence_spans"],
    "properties": {
        "chapter_number": {"type": "integer"},
        "location_change": {"type": ["string","null"]},
        "thien_cong_changes": {"type": "object"},
        "items_acquired": {"type": "object"},
        "items_consumed": {"type": "object"},
        "evidence_spans": {"type": "array", "items": {"type": "string"}},
        "evidence_locators": {"type": "array"},
        "inference_type": {"enum": ["extracted","inferred"]},
    }
}

class LLMExtractor:
    def __init__(self, model_router=None):
        self.model_router = model_router

    def extract_with_llm(self, chapter_num: int, draft_text: str, current_state: Dict[str,Any], llm_call=None) -> Dict[str,Any]:
        """
        Nếu có llm_call: gọi LLM với schema, validate evidence substring.
        Nếu không: fallback regex (giữ nguyên hành vi hiện tại).
        """
        if llm_call is None:
            # Fallback: dùng StoryStateManager regex hiện có
            from fanfic_pipeline.core.story_state import StoryStateManager
            delta = StoryStateManager.extract_state_delta(chapter_num, draft_text, current_state)
            return delta.model_dump()
        # LLM path
        prompt = f"Extract StateDelta as JSON per schema. Draft (first 2000 chars):\\n{draft_text[:2000]}"
        raw = llm_call(prompt, STATEDELTA_SCHEMA)
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except:
            data = {"chapter_number": chapter_num, "evidence_spans": [], "inference_type": "inferred"}
        # Validate evidence substring (BUG-06 invariant)
        valid_spans = [s for s in data.get("evidence_spans", []) if s and s in draft_text]
        if len(valid_spans) != len(data.get("evidence_spans", [])):
            data["inference_type"] = "inferred"
        data["evidence_spans"] = valid_spans
        return data

    def validate_against_regex(self, llm_delta: Dict[str,Any], regex_delta: Dict[str,Any]) -> List[str]:
        """So sánh LLM vs regex, trả về discrepancies (validator chéo)."""
        diffs=[]
        for field in ["location_change","thien_cong_changes","items_acquired"]:
            if llm_delta.get(field) != regex_delta.get(field):
                diffs.append(f"{field}: llm={llm_delta.get(field)} vs regex={regex_delta.get(field)}")
        return diffs
