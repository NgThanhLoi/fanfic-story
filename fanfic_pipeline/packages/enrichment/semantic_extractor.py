"""
Semantic Extractor: LLM-driven semantic knowledge extraction (relationships, causal links, epistemic boundaries, arc summaries, and newly discovered entities feedback loop).
"""
import json, re
from typing import List, Dict, Any, Optional, Tuple
from fanfic_pipeline.packages.enrichment.enrichment_store import (
    EnrichedRelationship, EnrichedCausalLink, EpistemicRecord, ArcSummaryRecord, EnrichedEntity
)
from fanfic_pipeline.packages.canon.alias_normalizer import normalize_fold

class SemanticExtractor:
    def __init__(self, model_invoker: Optional[Any] = None):
        self.model_invoker = model_invoker

    def extract_from_window(
        self,
        window_id: int,
        start_chapter: int,
        end_chapter: int,
        chunks: List[Any],
        known_entities: List[EnrichedEntity]
    ) -> Tuple[List[EnrichedEntity], List[EnrichedRelationship], List[EnrichedCausalLink], List[EpistemicRecord], ArcSummaryRecord]:
        if self.model_invoker:
            try:
                return self._extract_with_llm(window_id, start_chapter, end_chapter, chunks, known_entities)
            except Exception as e:
                # Fallback to heuristic
                pass

        return self._extract_heuristic(window_id, start_chapter, end_chapter, chunks, known_entities)

    def _extract_heuristic(
        self,
        window_id: int,
        start_chapter: int,
        end_chapter: int,
        chunks: List[Any],
        known_entities: List[EnrichedEntity]
    ) -> Tuple[List[EnrichedEntity], List[EnrichedRelationship], List[EnrichedCausalLink], List[EpistemicRecord], ArcSummaryRecord]:
        discovered_entities: List[EnrichedEntity] = []
        rels: List[EnrichedRelationship] = []
        causal: List[EnrichedCausalLink] = []
        epistemic: List[EpistemicRecord] = []

        char_entities = [e for e in known_entities if e.entity_type == "character"]
        active_chars_set = set()

        for chunk in chunks:
            text = chunk.text if hasattr(chunk, "text") else (chunk.get("text", "") if isinstance(chunk, dict) else "")
            ch_idx = start_chapter
            if hasattr(chunk, "spine_order"): ch_idx = chunk.spine_order
            elif hasattr(chunk, "chapter_index"): ch_idx = chunk.chapter_index
            elif isinstance(chunk, dict): ch_idx = chunk.get("chapter_index", chunk.get("spine_order", start_chapter))

            if not text:
                continue

            present_chars = []
            for c in char_entities:
                for a in [c.canonical_name] + c.aliases:
                    if a in text:
                        present_chars.append(c.id)
                        active_chars_set.add(c.canonical_name)
                        break

            if len(present_chars) >= 2:
                c1, c2 = present_chars[0], present_chars[1]
                if c1 != c2:
                    rel_type = "ally"
                    if "địch" in text or "sát" in text or "chiến" in text:
                        rel_type = "adversary"
                    elif "sư phụ" in text or "đệ tử" in text or "sư huynh" in text:
                        rel_type = "master_student"

                    evidence_snip = text[:min(len(text), 120)].strip()
                    rels.append(EnrichedRelationship(
                        from_entity=c1,
                        to_entity=c2,
                        type=rel_type,
                        since_chapter=ch_idx,
                        evidence=evidence_snip,
                        confidence=0.75
                    ))

        summary_text = f"Cụm chương {start_chapter}-{end_chapter}: Giai đoạn khám phá và thử thách ban đầu của các nhân vật chính."
        major_events = [f"Chương {start_chapter}: Khởi đầu mốc thử luyện", f"Chương {end_chapter}: Tổng kết giai đoạn"]

        summary = ArcSummaryRecord(
            window_id=window_id,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            summary_text=summary_text,
            major_events=major_events,
            active_characters=list(active_chars_set)[:10]
        )

        return discovered_entities, rels, causal, epistemic, summary

    def _extract_with_llm(
        self,
        window_id: int,
        start_chapter: int,
        end_chapter: int,
        chunks: List[Any],
        known_entities: List[EnrichedEntity]
    ) -> Tuple[List[EnrichedEntity], List[EnrichedRelationship], List[EnrichedCausalLink], List[EpistemicRecord], ArcSummaryRecord]:
        corpus_sample = "\n\n".join([
            (c.text if hasattr(c, "text") else (c.get("text", "") if isinstance(c, dict) else str(c)))[:350]
            for c in chunks[:8]
        ])
        known_names = [e.canonical_name for e in known_entities][:15]

        prompt = f"""Dựa vào trích đoạn tiểu thuyết sau, trích xuất JSON tri thức:
- Danh sách thực thể ĐÃ BIẾT (không cần trích lại): {known_names}

Hãy trả về DUY NHẤT một khối JSON hợp lệ:
{{
  "discovered_entities": [
    {{"name": "Tên_thực_thể", "aliases": [], "type": "character|location|technique|sect", "evidence": "trích đoạn ngắn nguyên tác"}}
  ],
  "relationships": [
    {{"from_entity": "Tên_1", "to_entity": "Tên_2", "type": "master_student|ally|adversary", "since_chapter": {start_chapter}, "evidence": "trích đoạn ngắn"}}
  ],
  "causal_links": [],
  "epistemic_records": [],
  "arc_summary": {{
    "summary_text": "Tóm tắt 1 câu",
    "major_events": ["Sự kiện chính 1"],
    "active_characters": ["Nhân vật 1"]
  }}
}}

Trích đoạn nguyên tác:
{corpus_sample}
"""
        response = self.model_invoker.call_agent_llm(
            "architect_agent",
            user_prompt=prompt,
            system_prompt="You are an expert NLP entity and knowledge extractor for Chinese Xianxia web novels. Output valid JSON only."
        )
        m = re.search(r"\{.*\}", response, re.DOTALL)
        if not m:
            raise ValueError("LLM response did not contain JSON")
        data = json.loads(m.group(0))


        discovered = [
            EnrichedEntity(
                id=f"ENT:{d.get('type','char')}:{normalize_fold(d.get('name','')).replace(' ', '_')}",
                canonical_name=d.get("name", ""),
                aliases=d.get("aliases", []),
                first_seen_chapter=start_chapter,
                mention_count=1,
                entity_type=d.get("type", "character"),
                evidence=d.get("evidence", ""),
                source_chapter=start_chapter,
                confidence=0.85
            )
            for d in data.get("discovered_entities", [])
            if d.get("name")
        ]

        rels = [EnrichedRelationship(**r) for r in data.get("relationships", [])]
        causal = [EnrichedCausalLink(**c) for c in data.get("causal_links", [])]
        epistemic = [EpistemicRecord(**p) for p in data.get("epistemic_records", [])]
        arc_data = data.get("arc_summary", {})

        summary = ArcSummaryRecord(
            window_id=window_id,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            summary_text=arc_data.get("summary_text", f"Tóm tắt chương {start_chapter}-{end_chapter}"),
            major_events=arc_data.get("major_events", []),
            active_characters=arc_data.get("active_characters", [])
        )
        return discovered, rels, causal, epistemic, summary
