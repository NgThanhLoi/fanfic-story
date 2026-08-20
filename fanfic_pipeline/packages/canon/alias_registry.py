"""
Bilingual Entity & Alias Registry (FR-03 Compliant) — v1.1 Enhanced
Maps entities across Chinese (zh-CN) and Vietnamese (vi-VN) names, titles, aliases, and honorifics.
Provides canonical entity resolution with confidence scoring, provenance, and collision detection.
"""

from typing import Dict, List, Optional, Set, Any, Tuple, Union
from pydantic import BaseModel, Field
import re


class CanonicalEntity(BaseModel):
    entity_id: str
    entity_type: str  # character, faction, realm, technique, item, location
    canonical_name_vi: str
    canonical_name_zh: str = ""
    aliases_vi: List[str] = Field(default_factory=list)
    aliases_zh: List[str] = Field(default_factory=list)

    description: str = ""
    factions: List[str] = Field(default_factory=list)
    signature_traits: List[str] = Field(default_factory=list)


class AliasEntry(BaseModel):
    """Per-alias metadata with provenance and confidence."""
    alias: str
    normalized: str
    entity_id: str
    language: str  # vi | zh | unknown
    confidence: float = 1.0
    provenance: str = "default_registry"  # e.g. default_registry | corpus_enrichment | manual
    source_chunk_id: Optional[str] = None


class AliasRegistry:
    def __init__(self):
        self.entities: Dict[str, CanonicalEntity] = {}
        # normalized alias -> list of AliasEntry (to detect collisions)
        self.alias_index: Dict[str, List[AliasEntry]] = {}
        # backward compat: alias_to_id (first winner)
        self.alias_to_id: Dict[str, str] = {}
        # flat AliasEntry list
        self.alias_entries: List[AliasEntry] = []
        self._load_default_nhat_the_entities()

    # ------------------------------------------------------------------
    # Registration with provenance & confidence
    # ------------------------------------------------------------------
    def register_entity(self, entity: CanonicalEntity, provenance: str = "default_registry", confidence: float = 1.0):
        self.entities[entity.entity_id] = entity
        all_aliases_vi = [entity.canonical_name_vi] + entity.aliases_vi
        all_aliases_zh = [entity.canonical_name_zh] + entity.aliases_zh

        for alias in all_aliases_vi:
            norm = alias.strip().lower()
            if not norm:
                continue
            entry = AliasEntry(
                alias=alias.strip(),
                normalized=norm,
                entity_id=entity.entity_id,
                language="vi",
                confidence=confidence,
                provenance=provenance,
            )
            self._index_alias(entry)

        for alias in all_aliases_zh:
            norm = alias.strip().lower()
            if not norm:
                continue
            entry = AliasEntry(
                alias=alias.strip(),
                normalized=norm,
                entity_id=entity.entity_id,
                language="zh",
                confidence=confidence,
                provenance=provenance,
            )
            self._index_alias(entry)

    def _index_alias(self, entry: AliasEntry):
        norm = entry.normalized
        if norm not in self.alias_index:
            self.alias_index[norm] = []
        # Avoid duplicate entries for same entity+alias
        for existing in self.alias_index[norm]:
            if existing.entity_id == entry.entity_id and existing.alias == entry.alias:
                # update confidence/provenance if higher
                if entry.confidence > existing.confidence:
                    existing.confidence = entry.confidence
                    existing.provenance = entry.provenance
                return
        self.alias_index[norm].append(entry)
        self.alias_entries.append(entry)
        # Maintain backward-compat alias_to_id: first entry wins, but keep all in index
        if norm not in self.alias_to_id:
            self.alias_to_id[norm] = entry.entity_id

    def add_alias(
        self,
        entity_id: str,
        alias: str,
        language: str = "vi",
        confidence: float = 0.8,
        provenance: str = "manual",
        source_chunk_id: Optional[str] = None,
    ) -> bool:
        """Add a single alias to an existing entity with provenance."""
        if entity_id not in self.entities:
            return False
        norm = alias.strip().lower()
        if not norm:
            return False
        entry = AliasEntry(
            alias=alias.strip(),
            normalized=norm,
            entity_id=entity_id,
            language=language,
            confidence=confidence,
            provenance=provenance,
            source_chunk_id=source_chunk_id,
        )
        self._index_alias(entry)
        # Also update entity's alias list for completeness
        ent = self.entities[entity_id]
        if language == "vi" and alias.strip() not in ent.aliases_vi and alias.strip() != ent.canonical_name_vi:
            ent.aliases_vi.append(alias.strip())
        elif language == "zh" and alias.strip() not in ent.aliases_zh and alias.strip() != ent.canonical_name_zh:
            ent.aliases_zh.append(alias.strip())
        return True

    # ------------------------------------------------------------------
    # Resolution with collision detection
    # ------------------------------------------------------------------
    def resolve(self, query: str) -> Optional[CanonicalEntity]:
        """Legacy resolve: returns single entity (first match) for backward compat."""
        result = self.resolve_alias(query)
        if result is None:
            return None
        if "entity" in result and result["entity"] is not None:
            return result["entity"]
        if "candidates" in result and result["candidates"]:
            # Ambiguous: return highest-confidence candidate
            return result["candidates"][0]
        return None

    def resolve_alias(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Enhanced resolution.
        Returns:
          None if no match
          {"entity_id": str, "entity": CanonicalEntity, "confidence": float, "provenance": str} if unambiguous
          {"candidates": [CanonicalEntity], "candidate_ids": [str], "reason": "ambiguous", "matches": [AliasEntry]} if collision
        """
        q = query.strip().lower()
        if not q:
            return None

        # Exact match in index
        if q in self.alias_index:
            entries = self.alias_index[q]
            # Deduplicate by entity_id, keep highest confidence per entity
            by_entity: Dict[str, AliasEntry] = {}
            for e in entries:
                if e.entity_id not in by_entity or e.confidence > by_entity[e.entity_id].confidence:
                    by_entity[e.entity_id] = e
            if len(by_entity) == 1:
                eid = list(by_entity.keys())[0]
                ent = self.entities.get(eid)
                best = list(by_entity.values())[0]
                return {"entity_id": eid, "entity": ent, "confidence": best.confidence, "provenance": best.provenance, "matches": entries}
            else:
                # Collision: multiple entities share same alias
                candidates = [self.entities[eid] for eid in by_entity if eid in self.entities]
                # Sort by confidence desc
                candidates_sorted = sorted(candidates, key=lambda c: by_entity[c.entity_id].confidence, reverse=True)
                return {
                    "candidates": candidates_sorted,
                    "candidate_ids": [c.entity_id for c in candidates_sorted],
                    "reason": "ambiguous_alias_collision",
                    "query": query,
                    "matches": entries,
                }

        # Substring fallback: collect all aliases that contain query or vice versa
        substring_hits: List[AliasEntry] = []
        for norm, entries in self.alias_index.items():
            if norm in q or q in norm:
                substring_hits.extend(entries)
        if substring_hits:
            # Deduplicate by entity_id, keep highest confidence per entity
            by_entity2: Dict[str, AliasEntry] = {}
            for e in substring_hits:
                if e.entity_id not in by_entity2 or e.confidence > by_entity2[e.entity_id].confidence:
                    by_entity2[e.entity_id] = e
            if len(by_entity2) == 1:
                eid = list(by_entity2.keys())[0]
                ent = self.entities.get(eid)
                best = list(by_entity2.values())[0]
                return {"entity_id": eid, "entity": ent, "confidence": best.confidence * 0.85, "provenance": best.provenance, "matches": substring_hits}
            else:
                candidates = [self.entities[eid] for eid in by_entity2 if eid in self.entities]
                candidates_sorted = sorted(candidates, key=lambda c: by_entity2[c.entity_id].confidence, reverse=True)
                return {
                    "candidates": candidates_sorted,
                    "candidate_ids": [c.entity_id for c in candidates_sorted],
                    "reason": "ambiguous_substring_collision",
                    "query": query,
                    "matches": substring_hits,
                }

        return None

    def get_all_aliases(self, entity_id: str) -> List[str]:
        entity = self.entities.get(entity_id)
        if not entity:
            return []
        return [entity.canonical_name_vi, entity.canonical_name_zh] + entity.aliases_vi + entity.aliases_zh

    def get_alias_entries(self, entity_id: str) -> List[AliasEntry]:
        return [e for e in self.alias_entries if e.entity_id == entity_id]

    def expand_query_aliases(self, text: str) -> Set[str]:
        """Expands keywords in text to all bilingual aliases for search recall."""
        expanded = set(text.split())
        for word in text.split():
            res = self.resolve_alias(word)
            if res and "entity" in res and res["entity"]:
                for a in self.get_all_aliases(res["entity"].entity_id):
                    expanded.add(a)
            elif res and "candidates" in res:
                for cand in res["candidates"]:
                    for a in self.get_all_aliases(cand.entity_id):
                        expanded.add(a)
        return expanded

    def detect_collisions(self) -> List[Dict[str, Any]]:
        """Returns all ambiguous aliases (where one alias maps to >1 entity)."""
        collisions: List[Dict[str, Any]] = []
        for norm, entries in self.alias_index.items():
            entity_ids = set(e.entity_id for e in entries)
            if len(entity_ids) > 1:
                collisions.append({
                    "alias": norm,
                    "entity_ids": list(entity_ids),
                    "entries": [{"alias": e.alias, "entity_id": e.entity_id, "confidence": e.confidence, "provenance": e.provenance} for e in entries],
                })
        return collisions

    def enrich_from_corpus(self, chunks: List[Any]) -> Dict[str, Any]:
        """
        Stub for corpus-based alias enrichment.
        In production, this would NER-scan CanonChunk texts to discover new aliases.
        Currently: scans chunk texts for known entity substrings and registers
        any new co-occurring capitalized phrases as low-confidence aliases.

        Returns stats dict.
        """
        if not chunks:
            return {"scanned": 0, "new_aliases": 0, "collisions": 0}

        new_aliases = 0
        # Very light heuristic: if chunk mentions an entity's canonical name,
        # look for parenthetical aliases like "Mạnh Kỳ (Tô Mạnh)" or "Mạnh Kỳ - Chân Định"
        alias_pattern = re.compile(r"([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-ỹ][a-zà-ỹ]+)*)\s*[\(（\-—]\s*([A-ZÀ-ỹ][a-zà-ỹ\s]+?)\s*[\)）]")

        for chunk in chunks:
            # chunk may be dict or CanonChunk
            if isinstance(chunk, dict):
                text = chunk.get("text") or chunk.get("content") or ""
                chunk_id = chunk.get("chunk_id") or chunk.get("id") or "unknown"
            else:
                text = getattr(chunk, "text", "") or getattr(chunk, "content", "") or str(chunk)
                chunk_id = getattr(chunk, "chunk_id", "unknown")

            if not text:
                continue

            # Find which entities are mentioned
            for entity in self.entities.values():
                if entity.canonical_name_vi.lower() in text.lower() or entity.canonical_name_zh in text:
                    # Look for parenthetical alias patterns near the mention
                    for m in alias_pattern.finditer(text):
                        potential_alias = m.group(2).strip()
                        if len(potential_alias) < 2 or len(potential_alias) > 20:
                            continue
                        norm = potential_alias.lower()
                        # Skip if already known
                        if norm in self.alias_index and any(e.entity_id == entity.entity_id for e in self.alias_index[norm]):
                            continue
                        # Register as low-confidence corpus-derived alias
                        self.add_alias(
                            entity_id=entity.entity_id,
                            alias=potential_alias,
                            language="vi",
                            confidence=0.55,
                            provenance="corpus_enrichment",
                            source_chunk_id=str(chunk_id),
                        )
                        new_aliases += 1

        collisions = len(self.detect_collisions())
        return {"scanned": len(chunks), "new_aliases": new_aliases, "collisions": collisions}

    def _load_default_nhat_the_entities(self):
        # 1. Mạnh Kỳ
        self.register_entity(CanonicalEntity(
            entity_id="char_meng_qi",
            entity_type="character",
            canonical_name_vi="Mạnh Kỳ",
            canonical_name_zh="孟奇",
            aliases_vi=["Chân Định", "Tô Mạnh", "Cuồng Đao Tô Mạnh", "Tô Tử Viễn", "Tiểu Hòa Thượng", "Lôi Đao Cuồng Tăng", "Nguyên Thủy Thiên Tôn"],
            aliases_zh=["真定", "苏孟", "狂刀苏孟", "苏子远", "小和尚", "雷刀狂僧", "原始天尊"],
            description="Nhân vật chính, người chuyển sinh, đao pháp Lôi Đao, tuyệt học Bát Cửu Huyền Công, Như Lai Thần Chưởng.",
            factions=["Tiểu đội Luân Hồi", "Thiếu Lâm Tự (cũ)", "Tiên Tích"],
            signature_traits=["Thích trang bức", "Sờ đầu trọc", "Siết chuôi đao", "Đao ý quyết đoán", "Trọng tình nghĩa"]
        ))

        # 2. Cố Tiểu Tang
        self.register_entity(CanonicalEntity(
            entity_id="char_gu_xiaosang",
            entity_type="character",
            canonical_name_vi="Cố Tiểu Tang",
            canonical_name_zh="顾小桑",
            aliases_vi=["Tiểu Tang", "Yêu Nữ", "Thánh Nữ Tố Nữ Đạo", "Vô Thượng Thiên Ma"],
            aliases_zh=["小桑", "妖女", "素女道圣女", "无上天魔"],
            description="Thánh nữ Tố Nữ Đạo, thông minh tuyệt đỉnh, hóa thân dự phòng của Vô Sinh Lão Mẫu.",
            factions=["Tố Nữ Đạo", "Ma Môn Lục Đạo"],
            signature_traits=["Gọi 'Tướng công'", "Cười giấu dao", "Chân trần áo trắng", "Tâm tư thâm sâu", "Cô tịch"]
        ))

        # 3. Giang Chỉ Vi
        self.register_entity(CanonicalEntity(
            entity_id="char_jiang_zhiwei",
            entity_type="character",
            canonical_name_vi="Giang Chỉ Vi",
            canonical_name_zh="江芷微",
            aliases_vi=["Chỉ Vi", "Kiếm Xuất Vô Hối", "Tẩy Kiếm Các truyền nhân"],
            aliases_zh=["芷微", "剑出无悔", "洗剑阁传人"],
            description="Truyền nhân Tẩy Kiếm Các, kiếm tâm thuần túy, phóng khoáng hào sảng.",
            factions=["Tẩy Kiếm Các", "Tiểu đội Luân Hồi"],
            signature_traits=["Kiếm xuất vô hối", "Thẳng thắn hào sảng", "Ánh mắt sáng như kiếm quang"]
        ))

        # 4. Tề Chính Ngôn
        self.register_entity(CanonicalEntity(
            entity_id="char_qi_zhengyan",
            entity_type="character",
            canonical_name_vi="Tề Chính Ngôn",
            canonical_name_zh="齐正言",
            aliases_vi=["Tề sư huynh", "Mặt đơ", "Ma Hoàng truyền nhân"],
            aliases_zh=["齐师兄", "面瘫", "魔皇传人"],
            description="Đệ tử Hoán Hoa Kiếm Phái, thừa kế Ma Hoàng điển tịch, khát vọng bình đẳng chúng sinh.",
            factions=["Hoán Hoa Kiếm Phái", "Tiểu đội Luân Hồi", "Ma Hoàng phái"],
            signature_traits=["Mặt đơ ngàn năm", "Trầm ổn ít nói", "Thầm lặng bảo vệ đồng đội"]
        ))

        # 5. Nguyễn Ngọc Thư
        self.register_entity(CanonicalEntity(
            entity_id="char_ruan_yushu",
            entity_type="character",
            canonical_name_vi="Nguyễn Ngọc Thư",
            canonical_name_zh="阮玉书",
            aliases_vi=["Ngọc Thư", "Lang Nha Nguyễn Thị"],
            aliases_zh=["玉书", "琅琊阮氏"],
            description="Tiểu thư Lang Nha Nguyễn thị, cầm kỹ trác tuyệt, mê ẩm thực và đồ ăn vặt.",
            factions=["Lang Nha Nguyễn Thị", "Tiểu đội Luân Hồi"],
            signature_traits=["Ôm cổ cầm Phượng Tê", "Thích ăn cá khô và bánh ngọt", "Ngoài lạnh trong nóng"]
        ))

        # 6. Tuyệt học & Chiêu thức
        self.register_entity(CanonicalEntity(
            entity_id="tech_bat_cuu_huyen_cong",
            entity_type="technique",
            canonical_name_vi="Bát Cửu Huyền Công",
            canonical_name_zh="八九玄功",
            aliases_vi=["Bát Cửu", "Huyền Công", "Cửu Chuyển Huyền Công"],
            aliases_zh=["八九", "玄功", "七十二变"],
            description="Tuyệt học Đạo môn đệ nhất hộ thể và biến hóa, nhục thân bất hoại, vạn pháp bất xâm."
        ))
        self.register_entity(CanonicalEntity(
            entity_id="tech_nhu_lai_than_chuong",
            entity_type="technique",
            canonical_name_vi="Như Lai Thần Chưởng",
            canonical_name_zh="如来神掌",
            aliases_vi=["Thần Chưởng", "Duy Ngã Độc Tôn"],
            aliases_zh=["神掌", "唯我独尊"],
            description="Phật môn chí cao tuyệt học, chia làm 9 thức, chấn nhiếp chư thiên."
        ))
        self.register_entity(CanonicalEntity(
            entity_id="tech_tiet_thien_that_kiem",
            entity_type="technique",
            canonical_name_vi="Tiệt Thiên Thất Kiếm",
            canonical_name_zh="截天七剑",
            aliases_vi=["Tiệt Thiên"],
            aliases_zh=["截天"],
            description="Đạo Đức/Linh Bảo kiếm pháp vô thượng, chặt đứt đạo tắc càn khôn."
        ))

        # 7. Cảnh giới
        self.register_entity(CanonicalEntity(
            entity_id="realm_khai_khieu",
            entity_type="realm",
            canonical_name_vi="Khai Khiếu",
            canonical_name_zh="开窍",
            aliases_vi=["Khai Khiếu cảnh", "Cửu Khiếu", "Tề Khiếu"],
            aliases_zh=["开窍境", "九窍", "齐窍"],
            description="Cảnh giới đả thông cửu khiếu thân thể, cảm ứng thiên địa sơ khai."
        ))
        self.register_entity(CanonicalEntity(
            entity_id="realm_ngoai_canh",
            entity_type="realm",
            canonical_name_vi="Ngoại Cảnh",
            canonical_name_zh="外景",
            aliases_vi=["Ngoại Cảnh cảnh", "Thiên Nhân Hợp Nhất", "Cửu Trọng Thiên"],
            aliases_zh=["外景境", "天人合一", "九重天"],
            description="Cảnh giới dẫn động thiên địa nguyên khí, nội ngoại giao hòa, chia 1 đến 9 Trọng Thiên."
        ))
        self.register_entity(CanonicalEntity(
            entity_id="realm_phap_than",
            entity_type="realm",
            canonical_name_vi="Pháp Thân",
            canonical_name_zh="法身",
            aliases_vi=["Nhân Tiên", "Địa Tiên", "Thiên Tiên"],
            aliases_zh=["法身", "地仙", "天仙"],
            description="Thoát phàm nhập thánh, ngưng tụ bất diệt Pháp Thân."
        ))
        self.register_entity(CanonicalEntity(
            entity_id="realm_bi_ngan",
            entity_type="realm",
            canonical_name_vi="Bỉ Ngạn",
            canonical_name_zh="彼岸",
            aliases_vi=["Đạo Quả", "Bỉ Ngạn đại năng", "Khổ hải bỉ ngạn"],
            aliases_zh=["彼岸", "道果", "苦海彼岸"],
            description="Siêu thoát dòng sông thời gian, nhìn thấu quá khứ tương lai, chưởng quản vạn giới vận mệnh."
        ))
