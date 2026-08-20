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

        # 2. Martial Arts (Ground Truth + Dynamic Pattern Mining across 1409 chapters)
        mined_techniques = self._mine_dynamic_techniques()
        for art_name, info in mined_techniques.items():
            first_ch = info["first_ch"]
            sample_ev = info["evidence"]
            count = info["count"]
            self.enrichment_store.add_entities([
                EnrichedEntity(
                    id=f"ART:{stats['martial_arts']+1:04d}",
                    canonical_name=art_name,
                    entity_type="technique",
                    aliases=[art_name] + info.get("cn", []),
                    first_seen_chapter=first_ch,
                    mention_count=count,
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

    def _mine_dynamic_techniques(self) -> Dict[str, Dict[str, Any]]:
        import re
        results: Dict[str, Dict[str, Any]] = {}
        # 1. VIP ground truth arts
        for art_vn, info in DIVINE_MARTIAL_ARTS.items():
            cn_keys = info.get("cn", [])
            hits = []
            for k in cn_keys:
                hits.extend(self.canon_store.search_canon(k, top_k=10))
            first_ch = min((h.get("chapter", 9999) for h in hits), default=1)
            sample_ev = hits[0].get("text", "")[:200] if hits else info.get("desc", "")
            results[art_vn] = {
                "cn": cn_keys,
                "first_ch": first_ch if first_ch != 9999 else 1,
                "count": max(len(hits), 1),
                "evidence": sample_ev
            }

        # 2. Dynamic regex mining across all 1409 chapters
        pattern = re.compile(r"[\u4e00-\u9fa5]{2,6}(?:剑法|刀法|神掌|神功|真经|秘典|玄功|心法|神拳|指法|步法|绝技|魔功|雷法|剑诀|刀诀|剑经|琴谱|阵法|秘术|天功|掌法|棍法|枪法|锤法|神指|身法|化诀|奇功|大法)")
        stop_chars = set("的是和了在与他我你之被把各种等门套招门有这那几本所修炼以展开")


        for chunk in self.canon_store.chunks.values():
            text = chunk.get("text", "")
            ch_idx = chunk.get("chapter_index", 1)
            for m in pattern.findall(text):
                if 3 <= len(m) <= 7 and not any(c in m for c in stop_chars):
                    if m not in results:
                        results[m] = {
                            "cn": [m],
                            "first_ch": ch_idx,
                            "count": 0,
                            "evidence": text[:200]
                        }
                    results[m]["count"] += 1
                    results[m]["first_ch"] = min(results[m]["first_ch"], ch_idx)

        # Keep techniques with count >= 2 or VIP ground truth
        return {k: v for k, v in results.items() if v["count"] >= 2 or k in DIVINE_MARTIAL_ARTS}

