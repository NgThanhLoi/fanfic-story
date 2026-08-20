"""
Batch Orchestrator: Drives window-based batch enrichment across EPUB corpus chunks.
"""
import os, pathlib
from typing import List, Dict, Any, Optional
from fanfic_pipeline.packages.canon.canon_store import CanonStore
from fanfic_pipeline.packages.enrichment.enrichment_store import EnrichmentStore
from fanfic_pipeline.packages.enrichment.structural_extractor import StructuralExtractor
from fanfic_pipeline.packages.enrichment.semantic_extractor import SemanticExtractor
from fanfic_pipeline.packages.enrichment.evidence_validator import EvidenceValidator
from fanfic_pipeline.packages.enrichment.checkpoint import EnrichmentCheckpoint

class BatchOrchestrator:
    def __init__(
        self,
        canon_store: CanonStore,
        enrichment_store: EnrichmentStore,
        checkpoint_path: str,
        model_invoker: Optional[Any] = None
    ):
        self.canon_store = canon_store
        self.enrichment_store = enrichment_store
        self.checkpoint_path = checkpoint_path
        self.structural_extractor = StructuralExtractor()
        self.semantic_extractor = SemanticExtractor(model_invoker=model_invoker)
        self.validator = EvidenceValidator()
        self.checkpoint = EnrichmentCheckpoint.load(checkpoint_path)

    def run(
        self,
        max_chapters: Optional[int] = None,
        window_size: int = 30,
        resume: bool = True,
        structural_only: bool = False
    ) -> Dict[str, Any]:
        # Determine total chapters available in CanonStore
        total_chapters = 1409
        if hasattr(self.canon_store, "chapters") and self.canon_store.chapters:
            total_chapters = len(self.canon_store.chapters)
        elif hasattr(self.canon_store, "spans") and self.canon_store.spans:
            total_chapters = max((getattr(s, "spine_order", 1) for s in self.canon_store.spans.values()), default=1409)

        if max_chapters is not None:
            total_chapters = min(total_chapters, max_chapters)

        num_windows = (total_chapters + window_size - 1) // window_size

        for w_idx in range(num_windows):
            window_id = w_idx + 1
            start_ch = w_idx * window_size + 1
            end_ch = min((w_idx + 1) * window_size, total_chapters)

            if resume and self.checkpoint.is_window_completed(window_id):
                continue

            # 1. Fetch chunks for window from CanonStore
            chunks = self._load_chunks_in_range(start_ch, end_ch)
            if not chunks:
                self.checkpoint.mark_window_completed(window_id, end_ch, self.enrichment_store.stats())
                self.checkpoint.save(self.checkpoint_path)
                continue

            # 2. Structural extraction (zero-token)
            struct_entities = self.structural_extractor.extract_from_chunks(chunks, current_chapter=start_ch)
            valid_entities = []
            for ent in struct_entities:
                ok, _ = self.validator.validate(ent, chunks)
                if ok:
                    valid_entities.append(ent)
            self.enrichment_store.add_entities(valid_entities)

            # 3. Semantic extraction (relationships, causal links, epistemic, arc summary, discovered entities)
            if not structural_only:
                all_known = self.enrichment_store.query_all_entities()
                discovered, rels, causal, epistemic, summary = self.semantic_extractor.extract_from_window(
                    window_id=window_id,
                    start_chapter=start_ch,
                    end_chapter=end_ch,
                    chunks=chunks,
                    known_entities=all_known
                )
                valid_discovered = [d for d in discovered if self.validator.validate(d, chunks)[0]]
                valid_rels = [r for r in rels if self.validator.validate(r, chunks)[0]]
                valid_causal = [c for c in causal if self.validator.validate(c, chunks)[0]]
                valid_epistemic = [p for p in epistemic if self.validator.validate(p, chunks)[0]]

                # Feed discovered entities back into enrichment store & alias registry
                if valid_discovered:
                    self.enrichment_store.add_entities(valid_discovered)
                    if hasattr(self.canon_store, "alias_registry") and self.canon_store.alias_registry:
                        from fanfic_pipeline.packages.canon.alias_registry import CanonicalEntity
                        for d in valid_discovered:
                            try:
                                self.canon_store.alias_registry.register_entity(
                                    CanonicalEntity(
                                        entity_id=d.id,
                                        canonical_name_vi=d.canonical_name,
                                        aliases_vi=d.aliases,
                                        entity_type=d.entity_type
                                    ),
                                    provenance="llm_discovery"
                                )
                            except Exception:
                                pass

                self.enrichment_store.add_relationships(valid_rels)
                self.enrichment_store.add_causal_links(valid_causal)
                self.enrichment_store.add_epistemic(valid_epistemic)
                self.enrichment_store.add_arc_summary(summary)


            # 4. Checkpoint
            self.checkpoint.mark_window_completed(window_id, end_ch, self.enrichment_store.stats())
            self.checkpoint.save(self.checkpoint_path)

        return self.enrichment_store.stats()

    def _load_chunks_in_range(self, start_ch: int, end_ch: int) -> List[Any]:
        chunks = []
        if hasattr(self.canon_store, "spans") and self.canon_store.spans:
            for sid, span in self.canon_store.spans.items():
                order = getattr(span, "spine_order", 0)
                if start_ch <= order <= end_ch:
                    chunks.append(span)
        elif hasattr(self.canon_store, "chunks") and self.canon_store.chunks:
            for cid, chunk in self.canon_store.chunks.items():
                idx = chunk.get("chapter_index", chunk.get("spine_order", 0)) if isinstance(chunk, dict) else getattr(chunk, "chapter_index", 0)
                if start_ch <= idx <= end_ch:
                    chunks.append(chunk)
        return chunks

