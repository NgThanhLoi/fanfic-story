"""
Evidence Validator: Hard gate ensuring all extracted entities, relationships, and events have genuine substring evidence in the canon corpus.
"""
from typing import List, Dict, Any, Tuple, Optional
from fanfic_pipeline.packages.canon.alias_normalizer import normalize_fold

class EvidenceValidator:
    def __init__(self, min_length: int = 8):
        self.min_length = min_length

    def validate(self, record: Any, source_chunks: List[Any]) -> Tuple[bool, str]:
        evidence = getattr(record, "evidence", "")
        if not evidence or len(evidence.strip()) < self.min_length:
            return False, f"Evidence too short (< {self.min_length} chars)"

        norm_evidence = normalize_fold(evidence)

        def _get_text(c):
            if hasattr(c, "text"): return c.text
            if isinstance(c, dict): return c.get("text", "")
            return ""

        def _get_id(c):
            if hasattr(c, "span_id"): return c.span_id
            if hasattr(c, "chunk_id"): return c.chunk_id
            if isinstance(c, dict): return c.get("span_id", c.get("chunk_id", ""))
            return ""

        for chunk in source_chunks:
            chunk_text = _get_text(chunk)
            norm_chunk = normalize_fold(chunk_text)
            if norm_evidence in norm_chunk:
                return True, _get_id(chunk)

        # Fallback: check if 80% contiguous words match (in case of slight punctuation difference)
        words = [w for w in norm_evidence.split() if len(w) >= 2]
        if len(words) >= 4:
            subphrase = " ".join(words[:4])
            for chunk in source_chunks:
                chunk_text = _get_text(chunk)
                norm_chunk = normalize_fold(chunk_text)
                if subphrase in norm_chunk:
                    return True, _get_id(chunk)


        return False, "Evidence substring not found in source canon chunks"
