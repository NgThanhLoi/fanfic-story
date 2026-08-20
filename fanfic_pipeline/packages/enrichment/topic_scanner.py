"""
P1.9 — TopicDeepScanner: Hybrid Knowledge Engine connecting Ground Truth Lore with EPUB Text.
Searches CanonStore across 1409 chapters to find verbatim textual evidence and provenance.
"""
from typing import List, Dict, Any, Optional
from fanfic_pipeline.packages.canon.canon_store import CanonStore
from fanfic_pipeline.packages.enrichment.enrichment_store import EnrichmentStore, EnrichedEntity, EnrichedRelationship
from fanfic_pipeline.packages.canon.power_ladder import REALM_ORDER
from fanfic_pipeline.data.nhat_the_chi_ton.canon_ground_truth import FACTIONS_GROUND_TRUTH, DIVINE_MARTIAL_ARTS, COSMIC_RULES_LORE

class TopicDeepScanner:
    def __init__(self, canon_store: CanonStore, enrichment_store: EnrichmentStore):
        self.canon_store = canon_store
        self.enrichment_store = enrichment_store

    def scan_all_topics(self, top_k_per_topic: int = 10) -> Dict[str, int]:
        stats = {"realms": 0, "factions": 0, "martial_arts": 0}

        # 1. Ground Cultivation Realms
        for idx, realm in enumerate(REALM_ORDER):
            clean_name = realm.split(" (")[0]
            hits = self.canon_store.search_canon(clean_name, top_k=top_k_per_topic)
            if hits:
                first_ch = min((h.get("chapter", 9999) for h in hits), default=1)
                sample_ev = hits[0].get("text", "")[:200]
                self.enrichment_store.add_entities([
                    EnrichedEntity(
                        id=f"REALM:{idx+1:03d}",
                        canonical_name=realm,
                        entity_type="realm",
                        aliases=[clean_name],
                        first_seen_chapter=first_ch if first_ch != 9999 else 1,
                        mention_count=len(hits),
                        evidence=sample_ev
                    )
                ])
                stats["realms"] += 1

        # 2. Ground Martial Arts
        for idx, (art, desc) in enumerate(DIVINE_MARTIAL_ARTS.items()):
            hits = self.canon_store.search_canon(art, top_k=top_k_per_topic)
            first_ch = min((h.get("chapter", 9999) for h in hits), default=1)
            sample_ev = hits[0].get("text", "")[:200] if hits else desc
            self.enrichment_store.add_entities([
                EnrichedEntity(
                    id=f"ART:{idx+1:03d}",
                    canonical_name=art,
                    entity_type="technique",
                    aliases=[art],
                    first_seen_chapter=first_ch if first_ch != 9999 else 1,
                    mention_count=len(hits),
                    evidence=sample_ev
                )
            ])
            stats["martial_arts"] += 1

        # 3. Ground Factions
        idx_fac = 0
        for ftype, factions in FACTIONS_GROUND_TRUTH.items():
            for fac in factions:
                idx_fac += 1
                fac_name = fac.split(" (")[0]
                hits = self.canon_store.search_canon(fac_name, top_k=top_k_per_topic)
                first_ch = min((h.get("chapter", 9999) for h in hits), default=1)
                sample_ev = hits[0].get("text", "")[:200] if hits else fac
                self.enrichment_store.add_entities([
                    EnrichedEntity(
                        id=f"SECT:{idx_fac:03d}",
                        canonical_name=fac_name,
                        entity_type="sect",
                        aliases=[fac_name],
                        first_seen_chapter=first_ch if first_ch != 9999 else 1,
                        mention_count=len(hits),
                        evidence=sample_ev
                    )
                ])
                stats["factions"] += 1

        return stats

