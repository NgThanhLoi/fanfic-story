"""
P4.1 — Canon Graph v2: SQLite-backed causal graph integrating EnrichedCausalLink with Butterfly Engine.
"""
from typing import List, Dict, Any, Optional
from pydantic import ConfigDict
from fanfic_pipeline.butterfly.causal_graph import CausalGraph, CausalEdge
from fanfic_pipeline.packages.enrichment.enrichment_store import EnrichedCausalLink, EnrichmentStore

class CanonGraphV2(CausalGraph):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def sync_from_enrichment(self, store: EnrichmentStore):
        links = store.query_causal_links()
        for link in links:
            self.edges.append(CausalEdge(
                src=link.cause_event,
                dst=link.effect_event,
                strength=link.confidence,
                necessity=link.necessity
            ))
            if link.cause_event not in self.events:
                self.events[link.cause_event] = {"scope": "local", "preconditions": []}
            if link.effect_event not in self.events:
                self.events[link.effect_event] = {"scope": "local", "preconditions": [link.cause_event], "necessity": link.necessity}
                self.fact_to_events.setdefault(link.cause_event, []).append(link.effect_event)

    def import_causal_links(self, links: List[EnrichedCausalLink]):
        for link in links:
            self.edges.append(CausalEdge(
                src=link.cause_event,
                dst=link.effect_event,
                strength=link.confidence,
                necessity=link.necessity
            ))
