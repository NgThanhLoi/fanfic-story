"""
P1.1 — Alias Normalizer (SPEC §A1 + §8.1 A-T1):
- Fold dấu tiếng Việt (NFD), hạ chữ, map CJK↔Hán-Việt (thông qua AliasRegistry)
- Biệt danh, đại từ tôn xưng (Tướng công, sư huynh, v.v.)
- Query expansion 2 chiều: mỗi từ trong query → tất cả alias của entity đó
- Chuẩn để toàn pipeline dùng chung (canon retrieval, spine entity, epistemic)
"""
import re, unicodedata
from typing import List, Set, Dict
from fanfic_pipeline.packages.canon.alias_registry import AliasRegistry
from pydantic import BaseModel, Field

def strip_diacritics(s: str) -> str:
    """Bỏ dấu tiếng Việt, giữ nguyên CJK."""
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('Đ', 'D').replace('đ', 'd')
    return s

def normalize_fold(s: str) -> str:
    """Lower + strip diacritics — dùng cho so sánh không phân biệt dấu."""
    return strip_diacritics(s.lower().strip())

def tokenize_vi(s: str) -> List[str]:
    """Tách từ tiếng Việt (giữ nguyên từ ghép 2 tiếng như Giang Chỉ Vi)."""
    # Đơn giản: split theo khoảng trắng + dấu câu
    return [w for w in re.split(r'[\s,.;:!?()\[\]{}"\'/\\|]+', s) if w]

class AliasNormalizer:
    """Wrapper quanh AliasRegistry để chuẩn hoá và mở rộng truy vấn."""
    def __init__(self):
        self._registry = AliasRegistry()
        # Build fold map: normalized (no diacritics, lower) -> entity_ids
        self.fold_index: Dict[str, List[str]] = {}
        # expanded alias map: original alias -> folded
        self.alias_fold: Dict[str, str] = {}
        # CJK->vi reverse map
        self.cjk_to_vi: Dict[str, str] = {}
        self._build_indices()

    def _build_indices(self):
        for entry in self._registry.alias_entries:
            fold = normalize_fold(entry.alias)
            self.alias_fold[entry.alias] = fold
            if fold not in self.fold_index:
                self.fold_index[fold] = []
            if entry.entity_id not in self.fold_index[fold]:
                self.fold_index[fold].append(entry.entity_id)
        # CJK->vi: lấy canonical zh/vi của mỗi entity
        for eid, ent in self._registry.entities.items():
            if ent.canonical_name_zh:
                self.cjk_to_vi[ent.canonical_name_zh] = ent.canonical_name_vi
                self.cjk_to_vi[normalize_fold(ent.canonical_name_zh)] = ent.canonical_name_vi
            for a in ent.aliases_zh:
                self.cjk_to_vi[a] = ent.canonical_name_vi

    # --- Core API ---
    def normalize(self, s: str) -> str:
        return normalize_fold(s)

    def canonicalize(self, mention: str) -> str:
        """Mention -> canonical_name_vi nếu tìm thấy, giữ nguyên nếu không."""
        # Fold lookup first (covers both diacritic and non)
        fold = normalize_fold(mention)
        if fold in self.fold_index:
            for eid in self.fold_index[fold]:
                ent = self._registry.entities.get(eid)
                if ent: return ent.canonical_name_vi
        r = self._registry.resolve_alias(mention)
        if r and r.get("entity_id"):
            ent = self._registry.entities.get(r["entity_id"])
            if ent: return ent.canonical_name_vi
            return r["entity_id"]
        if mention in self.cjk_to_vi:
            return self.cjk_to_vi[mention]
        if fold in self.cjk_to_vi:
            return self.cjk_to_vi[fold]
        return mention

    def expand_query(self, query: str) -> Set[str]:
        """
        Mở rộng query 2 chiều:
        - Mỗi token (có dấu) -> tất cả alias vi+zh của entity đó
        - Mỗi token CJK -> vi alias tương ứng
        - Trả về set chứa cả query gốc, folded, và các alias mở rộng
        """
        out: Set[str] = set()
        out.add(query)
        out.add(normalize_fold(query))
        # Phrase level (2-3 gram) — crucial for Vietnamese compound names like "Manh Ky"
        words = tokenize_vi(query)
        for n in (2, 3):
            for i in range(len(words)-n+1):
                phrase = " ".join(words[i:i+n])
                if len(phrase) < 4: continue
                # Try phrase as alias
                r = self._registry.resolve_alias(phrase)
                if r and r.get("entity_id"):
                    ent = self._registry.entities.get(r["entity_id"])
                    if ent:
                        out.add(ent.canonical_name_vi); out.add(normalize_fold(ent.canonical_name_vi))
                        out.add(ent.canonical_name_zh)
                        for a in ent.aliases_vi + ent.aliases_zh:
                            out.add(a); out.add(normalize_fold(a))
                        continue
                fold_phrase = normalize_fold(phrase)
                if fold_phrase in self.fold_index:
                    for eid in self.fold_index[fold_phrase]:
                        ent = self._registry.entities.get(eid)
                        if ent:
                            out.add(ent.canonical_name_vi); out.add(normalize_fold(ent.canonical_name_vi))
                            out.add(ent.canonical_name_zh)
                            for a in ent.aliases_vi + ent.aliases_zh:
                                out.add(a); out.add(normalize_fold(a))

        # Token level expansion
        for tok in tokenize_vi(query):
            if len(tok) < 2: continue
            # Direct alias hit
            r = self._registry.resolve_alias(tok)
            if r and r.get("entity_id"):
                ent = self._registry.entities.get(r["entity_id"])
                if ent:
                    out.add(ent.canonical_name_vi)
                    out.add(ent.canonical_name_zh)
                    for a in ent.aliases_vi + ent.aliases_zh:
                        out.add(a)
                        out.add(normalize_fold(a))
            else:
                # Fold hit
                fold = normalize_fold(tok)
                if fold in self.fold_index:
                    for eid in self.fold_index[fold]:
                        ent = self._registry.entities.get(eid)
                        if ent:
                            out.add(ent.canonical_name_vi)
                            out.add(ent.canonical_name_zh)
                            for a in ent.aliases_vi + ent.aliases_zh:
                                out.add(a)
                # CJK hit
                if tok in self.cjk_to_vi:
                    out.add(self.cjk_to_vi[tok])
                if fold in self.cjk_to_vi:
                    out.add(self.cjk_to_vi[fold])
        # Phrase level (query 2-3 tokens)
        # Thử cả query như phrase
        r_phrase = self._registry.resolve_alias(query)
        if r_phrase and r_phrase.get("entity_id"):
            ent = self._registry.entities.get(r_phrase["entity_id"])
            if ent:
                for a in [ent.canonical_name_vi, ent.canonical_name_zh] + ent.aliases_vi + ent.aliases_zh:
                    out.add(a); out.add(normalize_fold(a))
        return {x for x in out if x and len(x.strip()) >= 1}

    def expand_query_for_search(self, query: str) -> str:
        """Trả về chuỗi space-joined để append vào FTS query cho recall cao."""
        expanded = self.expand_query(query)
        # Ưu tiên: giữ query gốc + alias vi phổ biến
        vi_aliases = [a for a in expanded if re.search(r'[a-zA-Z\u00C0-\u024F]', a)][:12]
        zh_aliases = [a for a in expanded if re.search(r'[\u4e00-\u9fff]', a)][:8]
        return " ".join(vi_aliases + zh_aliases)

    def entity_spans(self, text: str) -> List[Dict]:
        """Tìm mọi mention của entity trong text (for spine/exam use)."""
        spans=[]
        folded_text = normalize_fold(text)
        for entry in self._registry.alias_entries:
            alias_fold = normalize_fold(entry.alias)
            if len(alias_fold) < 2: continue
            for m in re.finditer(re.escape(alias_fold), folded_text):
                spans.append({"alias": entry.alias, "entity_id": entry.entity_id, "start": m.start(), "end": m.end(), "confidence": entry.confidence})
        # Dedupe by (entity_id, span)
        spans.sort(key=lambda x: (x["start"], -len(x["alias"])))
        deduped=[]
        seen=set()
        for s in spans:
            key=(s["entity_id"], s["start"])
            if key not in seen:
                seen.add(key)
                deduped.append(s)
        return deduped

# Singleton
_instance = None
def get_alias_normalizer() -> AliasNormalizer:
    global _instance
    if _instance is None:
        _instance = AliasNormalizer()
    return _instance
