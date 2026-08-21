"""Retrieval package — VI canon store (FTS/BM25) + LSA router + style profile + rewrite loop."""
from fanfic_pipeline.packages.retrieval.vi_canon import ViCanonStore, tokenize, strip_diacritics
from fanfic_pipeline.packages.retrieval.style_profile import (
    analyze_text, refingerprint, fidelity, LsaRouter,
)
from fanfic_pipeline.packages.retrieval.style_rewrite import (
    StyleRewriteLoop, style_directives, style_hard_fail,
)

__all__ = [
    "ViCanonStore", "tokenize", "strip_diacritics",
    "analyze_text", "refingerprint", "fidelity", "LsaRouter",
    "StyleRewriteLoop", "style_directives", "style_hard_fail",
]
