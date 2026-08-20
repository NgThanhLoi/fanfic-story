"""
Structural Extractor: Rule-based, zero-token extraction of entities, aliases, realm milestones, locations, and techniques.
"""
import re
from typing import List, Dict, Any, Set, Tuple
from fanfic_pipeline.packages.canon.alias_normalizer import get_alias_normalizer, normalize_fold
from fanfic_pipeline.packages.enrichment.enrichment_store import EnrichedEntity

KNOWN_LOCATIONS = [
    "Thiếu Lâm", "Thiếu Lâm Tự", "Tẩy Kiếm Các", "Hoán Hoa Kiếm Phái", "Vạn Yêu Sơn",
    "Thần Đô", "Đại Lương", "Giang Đông", "Đông Hải", "Ẩn Hình Phường", "Trực Lục Tự",
    "Lục Đạo Luân Hồi", "Thái Bình Thành", "Huyền Thiên Tông", "Chân Vũ Tông", "Thuần Dương Tông",
    "Thao Thiết Cư", "Bồ Đề Viện", "Đạt Ma Viện", "Tạp Dịch Viện", "Tố Nữ Đạo"
]

KNOWN_TECHNIQUES = [
    "Bát Cửu Huyền Công", "Như Lai Thần Chưởng", "Thiên Ma Công", "Lạc Hồng Kiếm Pháp",
    "Thần Tiêu Cửu Diệt", "Đoạn Kim Đao Pháp", "Khai Thiên Cửu Kiếm", "A Nan Phá Giới Đao",
    "Tử Lôi Thất Kích", "Cửu Ấn Lục Đạo", "Thiên Ngoại Phi Tiên", "Diêm La Khốc", "Huyền Vũ Độn Pháp"
]

KNOWN_REALMS = [
    "Trúc Cơ", "Tích Khí", "Bách Nhật Trúc Cơ",
    "Khai Khiếu", "Nhất Khiếu", "Nhị Khiếu", "Tam Khiếu", "Tứ Khiếu", "Ngũ Khiếu", "Lục Khiếu", "Thất Khiếu", "Bát Khiếu", "Cửu Khiếu", "Cửu Khiếu Tề Khai",
    "Bán Bộ Ngoại Cảnh", "Ngoại Cảnh", "Thiên Nhân Hợp Nhất",
    "Ngoại Cảnh Nhất Trọng Thiên", "Ngoại Cảnh Nhị Trọng Thiên", "Ngoại Cảnh Tam Trọng Thiên",
    "Ngoại Cảnh Tứ Trọng Thiên", "Ngoại Cảnh Ngũ Trọng Thiên", "Ngoại Cảnh Lục Trọng Thiên",
    "Ngoại Cảnh Thất Trọng Thiên", "Ngoại Cảnh Bát Trọng Thiên", "Ngoại Cảnh Cửu Trọng Thiên",
    "Pháp Thân", "Địa Tiên", "Thiên Tiên", "Bán Bộ Truyền Thuyết", "Truyền Thuyết", "Tạo Hóa", "Bỉ Ngạn"
]

class StructuralExtractor:
    def __init__(self):
        self.normalizer = get_alias_normalizer()

    def extract_from_chunks(self, chunks: List[Any], current_chapter: int = 1) -> List[EnrichedEntity]:
        entities_dict: Dict[str, EnrichedEntity] = {}

        for chunk in chunks:
            text = chunk.text if hasattr(chunk, "text") else (chunk.get("text", "") if isinstance(chunk, dict) else "")
            ch_idx = current_chapter
            if hasattr(chunk, "spine_order"): ch_idx = chunk.spine_order
            elif hasattr(chunk, "chapter_index"): ch_idx = chunk.chapter_index
            elif isinstance(chunk, dict): ch_idx = chunk.get("chapter_index", chunk.get("spine_order", current_chapter))

            if not text:
                continue


            # 1. Extract known canonical entities via AliasNormalizer
            found_spans = self.normalizer.entity_spans(text)
            for span in found_spans:
                canon_id = span["entity_id"]
                matched_text = span["alias"]
                start, end = span["start"], span["end"]
                evidence_snippet = text[max(0, start - 20): min(len(text), end + 40)].strip()
                if canon_id not in entities_dict:
                    entity_spec = self.normalizer._registry.entities.get(canon_id)
                    cname = entity_spec.canonical_name_vi if entity_spec else matched_text
                    aliases = [matched_text]
                    if entity_spec:
                        aliases.extend(entity_spec.aliases_vi)
                        aliases.extend(entity_spec.aliases_zh)

                    entities_dict[canon_id] = EnrichedEntity(
                        id=canon_id,
                        canonical_name=cname,
                        aliases=list(set(aliases)),
                        first_seen_chapter=ch_idx,
                        mention_count=1,
                        entity_type="character",
                        evidence=evidence_snippet,
                        source_chapter=ch_idx,
                        confidence=span.get("confidence", 1.0)
                    )
                else:
                    entities_dict[canon_id].mention_count += 1
                    if matched_text not in entities_dict[canon_id].aliases:
                        entities_dict[canon_id].aliases.append(matched_text)


            # 2. Extract Location mentions
            for loc in KNOWN_LOCATIONS:
                idx = text.find(loc)
                if idx >= 0:
                    loc_id = f"LOC:{normalize_fold(loc).replace(' ', '_')}"
                    evidence_snippet = text[max(0, idx - 15): min(len(text), idx + len(loc) + 30)].strip()
                    if loc_id not in entities_dict:
                        entities_dict[loc_id] = EnrichedEntity(
                            id=loc_id,
                            canonical_name=loc,
                            aliases=[loc],
                            first_seen_chapter=ch_idx,
                            mention_count=1,
                            entity_type="location",
                            evidence=evidence_snippet,
                            source_chapter=ch_idx,
                            confidence=0.9
                        )
                    else:
                        entities_dict[loc_id].mention_count += 1

            # 3. Extract Technique mentions
            for tech in KNOWN_TECHNIQUES:
                idx = text.find(tech)
                if idx >= 0:
                    tech_id = f"TECH:{normalize_fold(tech).replace(' ', '_')}"
                    evidence_snippet = text[max(0, idx - 15): min(len(text), idx + len(tech) + 30)].strip()
                    if tech_id not in entities_dict:
                        entities_dict[tech_id] = EnrichedEntity(
                            id=tech_id,
                            canonical_name=tech,
                            aliases=[tech],
                            first_seen_chapter=ch_idx,
                            mention_count=1,
                            entity_type="technique",
                            evidence=evidence_snippet,
                            source_chapter=ch_idx,
                            confidence=0.9
                        )
                    else:
                        entities_dict[tech_id].mention_count += 1

            # 4. Extract Realm mentions
            for realm in KNOWN_REALMS:
                idx = text.find(realm)
                if idx >= 0:
                    realm_id = f"REALM:{normalize_fold(realm).replace(' ', '_')}"
                    evidence_snippet = text[max(0, idx - 15): min(len(text), idx + len(realm) + 30)].strip()
                    if realm_id not in entities_dict:
                        entities_dict[realm_id] = EnrichedEntity(
                            id=realm_id,
                            canonical_name=realm,
                            aliases=[realm],
                            first_seen_chapter=ch_idx,
                            mention_count=1,
                            entity_type="realm",
                            evidence=evidence_snippet,
                            source_chapter=ch_idx,
                            confidence=0.95
                        )
                    else:
                        entities_dict[realm_id].mention_count += 1

        return list(entities_dict.values())
