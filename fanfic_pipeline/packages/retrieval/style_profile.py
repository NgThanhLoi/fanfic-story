"""
P2 — LSA chapter router (numpy-only) + style_profile: 2 chế độ văn phong.

- lsa.py: vector chương VI/ZH từ .npy có sẵn (không cần joblib/scikit);
  query → nearest chapters bằng cosine trên vector trung bình token-overlap
  đơn giản (router thô, không phải dense neural — policy tắt dense vẫn chạy).
- style_profile.py: mode fanfic_voice | canon_mimicry + similarity scoring
  (spec §4.4); fingerprint là dẫn xuất từ corpus VI.
"""
import json
import math
import os
import re
import statistics
from collections import Counter
from typing import Any, Dict, List, Optional

import numpy as np

from fanfic_pipeline.packages.retrieval.vi_canon import tokenize, strip_diacritics

_RETRIEVAL_V2 = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "nhat_the_chi_ton", "vi_canon"))

# ---- fingerprint extraction (tính từ corpus, KHÔNG hard-code số liệu đo sẵn) ----

_WORD_RE = re.compile(r"[A-Za-zÀ-ỹĐđ]+")
_SENT_RE = re.compile(r"[^.!?…。！？\n]+(?:[.!?…]+|$)")


def analyze_text(text: str) -> Dict[str, Any]:
    body = "\n".join(x for x in text.splitlines()
                     if x.strip() not in ("***", "---", "___")).strip()
    paragraphs = [p.strip() for p in body.splitlines() if p.strip()]
    sentences = [m.group(0).strip() for m in _SENT_RE.finditer(body) if m.group(0).strip()]
    sent_words = [len(_WORD_RE.findall(s)) for s in sentences]
    dialogue = [p for p in paragraphs if "“" in p and "”" in p]
    attached = 0
    for p in dialogue:
        stripped = re.sub(r"“[^”]*”", "", p).strip(" ,.:;!?")
        attached += bool(stripped)
    return {
        "paragraph_count": len(paragraphs),
        "sentence_count": len(sentences),
        "avg_sentence_words": round(statistics.mean(sent_words), 2) if sent_words else 0,
        "avg_paragraph_chars": round(statistics.mean(map(len, paragraphs)), 2) if paragraphs else 0,
        "comma_per_10k_chars": round(body.count(",") / max(1, len(body)) * 10000, 2),
        "dialogue_paragraph_ratio": round(len(dialogue) / max(1, len(paragraphs)), 4) if paragraphs else 0,
        "short_sentence_ratio_lt10": round(sum(x < 10 for x in sent_words) / max(1, len(sent_words)), 4),
        "very_short_paragraph_ratio_lt60": round(sum(len(p) < 60 for p in paragraphs) / max(1, len(paragraphs)), 4),
    }


def refingerprint(corpus_dir: str, from_ch: int, to_ch: int) -> Dict[str, Any]:
    """Tính style_fingerprint từ corpus VI trong window [from_ch, to_ch]."""
    chunks_path = os.path.join(corpus_dir, "chunks.jsonl")
    by_chapter: Dict[int, List[str]] = {}
    with open(chunks_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            ch = r["global_chapter_no"]
            if from_ch <= ch <= to_ch:
                by_chapter.setdefault(ch, []).append(r["text"])
    all_metrics = [analyze_text("\n".join(texts))
                   for _, texts in sorted(by_chapter.items())]
    def mean(key):
        vals = [m[key] for m in all_metrics if m.get(key)]
        return round(statistics.mean(vals), 2) if vals else 0.0
    fp = {
        "window": {"from_chapter": from_ch, "to_chapter": to_ch,
                   "chapters": len(by_chapter)},
        "avg_sentence_words": mean("avg_sentence_words"),
        "avg_paragraph_chars": mean("avg_paragraph_chars"),
        "comma_per_10k_chars": mean("comma_per_10k_chars"),
        "dialogue_paragraph_ratio": mean("dialogue_paragraph_ratio"),
        "short_sentence_ratio_lt10": mean("short_sentence_ratio_lt10"),
        "very_short_paragraph_ratio_lt60": mean("very_short_paragraph_ratio_lt60"),
    }
    return fp


def fidelity(metrics: Dict[str, float], reference: Dict[str, float]) -> float:
    """Weighted-distance fidelity 0-100; công thức khai báo, tái-lập-được.
    Đường cong dịu: lệch tương đối ≤25% (ratio ≤0.08) vẫn ≥90 điểm."""
    scores = []
    for k in ("avg_sentence_words", "avg_paragraph_chars", "comma_per_10k_chars"):
        cur, ref = metrics.get(k), reference.get(k)
        if not cur or not ref:
            continue
        offset = abs(cur - ref) / ref
        scores.append(max(0.0, 1.0 - max(0.0, offset - 0.25) / 0.75))
    for k in ("short_sentence_ratio_lt10", "very_short_paragraph_ratio_lt60"):
        cur, ref = metrics.get(k), reference.get(k)
        if cur is None or ref is None:
            continue
        delta = abs(cur - ref)
        scores.append(max(0.0, 1.0 - max(0.0, delta - 0.08) / 0.32))
    if not scores:
        return 50.0
    return round(sum(scores) / len(scores) * 100, 1)


class LsaRouter:
    """Chapter-level router dùng LSA vectors có sẵn (.npy). Query được map vào
    không gian chapter bằng tf-idf-free heuristic: overlap-token centroid của
    top BM25 chapters (dùng vi_canon.search làm first-stage)."""

    def __init__(self, corpus_dir: Optional[str] = None):
        d = corpus_dir or _RETRIEVAL_V2
        self.vectors = np.load(os.path.join(d, "vi_lsa.npy")) \
            if os.path.exists(os.path.join(d, "vi_lsa.npy")) else \
            np.load(os.path.join(_RETRIEVAL_V2_FALLBACK(), "vi_chapter_lsa.npy"))
        self.chapters = json.load(open(
            os.path.join(_RETRIEVAL_V2_FALLBACK(), "vi_chapters.json"), encoding="utf-8"))
        self._row_to_ch = [c["global_chapter_no"] for c in self.chapters]

    def route(self, query: str, bm25_hits: List[Dict[str, Any]],
              top_k: int = 5, as_of_chapter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Second-stage: lấy các chapter chứa BM25 hits, tìm nearest LSA chapters
        theo cosine, trả về danh sách chapter gợi ý mở rộng ngữ cảnh."""
        seed_rows = []
        ch_to_row = {ch: i for i, ch in enumerate(self._row_to_ch)}
        for h in bm25_hits[:8]:
            row = ch_to_row.get(h["chapter_no"])
            if row is not None:
                seed_rows.append(row)
        if not seed_rows:
            return []
        centroid = self.vectors[seed_rows].mean(axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        vecs = self.vectors
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        sims = (vecs / norms) @ centroid
        order = np.argsort(-sims)
        out = []
        for idx in order:
            ch = self._row_to_ch[idx]
            if as_of_chapter is not None and ch > as_of_chapter:
                continue  # temporal boundary
            out.append({"chapter_no": int(ch), "similarity": round(float(sims[idx]), 4)})
            if len(out) >= top_k:
                break
        return out


def _RETRIEVAL_V2_FALLBACK() -> str:
    # vectors .npy giữ nguyên ở reference (read-only data); copy sang data dir khi import
    src = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "docs", "references",
        "yishizhizun-fanfic", "01_canon", "retrieval_v2"))
    dst = _RETRIEVAL_V2
    os.makedirs(dst, exist_ok=True)
    for name in ("vi_chapter_lsa.npy", "zh_chapter_lsa.npy", "vi_chapters.json",
                 "vi_meta.json", "zh_chapters.json", "zh_meta.json"):
        p_src = os.path.join(src, name)
        p_dst = os.path.join(dst, name)
        if os.path.exists(p_src) and not os.path.exists(p_dst):
            try:
                import shutil
                shutil.copy2(p_src, p_dst)
            except Exception:
                pass
    return dst
