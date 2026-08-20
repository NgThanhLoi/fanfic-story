"""
P1.9 — TopicDeepScanner: Bilingual (VN-CN) Knowledge Engine connecting Ground Truth Lore with EPUB Text.
Searches CanonStore across 1409 chapters using Chinese tokens and maps back to Vietnamese canonical taxonomy.
"""
from typing import List, Dict, Any, Optional
from fanfic_pipeline.packages.canon.canon_store import CanonStore
from fanfic_pipeline.packages.enrichment.enrichment_store import EnrichmentStore, EnrichedEntity
from fanfic_pipeline.data.nhat_the_chi_ton.canon_ground_truth import FACTIONS_GROUND_TRUTH, DIVINE_MARTIAL_ARTS, REALM_CN_MAP

class TopicDeepScanner:
    def __init__(self, canon_store: CanonStore, enrichment_store: EnrichmentStore):
        self.canon_store = canon_store
        self.enrichment_store = enrichment_store

    def scan_all_topics(self, top_k_per_topic: int = 20) -> Dict[str, int]:
        stats = {"realms": 0, "factions": 0, "martial_arts": 0}

        # 1. Realms (VN -> CN keys)
        for idx, (realm_vn, cn_keys) in enumerate(REALM_CN_MAP.items()):
            hits = []
            for k in cn_keys:
                hits.extend(self.canon_store.search_canon(k, top_k=top_k_per_topic))
            first_ch = min((h.get("chapter", 9999) for h in hits), default=1)
            sample_ev = hits[0].get("text", "")[:200] if hits else f"Cảnh giới tu vi bậc {idx+1}: {realm_vn}"
            self.enrichment_store.add_entities([
                EnrichedEntity(
                    id=f"REALM:{idx+1:03d}",
                    canonical_name=realm_vn,
                    entity_type="realm",
                    aliases=[realm_vn.split(" (")[0]] + cn_keys,
                    first_seen_chapter=first_ch if first_ch != 9999 else 1,
                    mention_count=max(len(hits), 1),
                    evidence=sample_ev
                )
            ])
            stats["realms"] += 1

        # 2. Martial Arts (VN -> CN keys)
        for idx, (art_vn, info) in enumerate(DIVINE_MARTIAL_ARTS.items()):
            cn_keys = info.get("cn", [])
            hits = []
            for k in cn_keys:
                hits.extend(self.canon_store.search_canon(k, top_k=top_k_per_topic))
            first_ch = min((h.get("chapter", 9999) for h in hits), default=1)
            sample_ev = hits[0].get("text", "")[:200] if hits else info.get("desc", "")
            self.enrichment_store.add_entities([
                EnrichedEntity(
                    id=f"ART:{idx+1:03d}",
                    canonical_name=art_vn,
                    entity_type="technique",
                    aliases=[art_vn] + cn_keys,
                    first_seen_chapter=first_ch if first_ch != 9999 else 1,
                    mention_count=max(len(hits), 1),
                    evidence=sample_ev
                )
            ])
            stats["martial_arts"] += 1

        # 3. Factions (VN -> CN keys)
        for idx, (fac_vn, info) in enumerate(FACTIONS_GROUND_TRUTH.items()):
            cn_keys = info.get("cn", [])
            hits = []
            for k in cn_keys:
                hits.extend(self.canon_store.search_canon(k, top_k=top_k_per_topic))
            first_ch = min((h.get("chapter", 9999) for h in hits), default=1)
            sample_ev = hits[0].get("text", "")[:200] if hits else info.get("desc", "")
            self.enrichment_store.add_entities([
                EnrichedEntity(
                    id=f"SECT:{idx+1:03d}",
                    canonical_name=fac_vn,
                    entity_type="sect",
                    aliases=[fac_vn] + cn_keys,
                    first_seen_chapter=first_ch if first_ch != 9999 else 1,
                    mention_count=max(len(hits), 1),
                    evidence=sample_ev
                )
            ])
            stats["factions"] += 1

        return stats
