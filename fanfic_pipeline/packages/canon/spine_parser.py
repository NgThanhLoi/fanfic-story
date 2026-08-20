
"""
Spine-Aware EPUB Ingestion Engine v1.1 (FR-01, FR-02 Compliant):
- Reads META-INF/container.xml + OPF manifest/spine in exact spine order
- Classifies ONLY by manifest href + heading/title semantics, NEVER prose substring for 卷
- CJK metrics: cjk_chars + cjk_tokens (CJK-aware) + whitespace_words
- Authority: source_href, spine_order, checksum, chapter_type per doc/chunk
"""
import zipfile, re, html, hashlib, os
import xml.etree.ElementTree as ET
try:
    from fanfic_pipeline.packages.canon.alias_registry import AliasRegistry as _AliasRegistry
    _alias_registry = _AliasRegistry()
except Exception:
    _alias_registry = None
from pathlib import Path
from typing import List, Dict, Any, Optional
from html.parser import HTMLParser
from pydantic import BaseModel, Field

# --- CJK ranges ---
CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3040-\u309f\u30a0-\u30ff]')

def cjk_metrics(html_text: str) -> Dict[str, int]:
    """Parse HTML properly, return cjk_chars, cjk_tokens, whitespace_words, total_chars."""
    # Strip script/style
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html_text, flags=re.DOTALL|re.IGNORECASE)
    # Strip tags
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    cjk_chars = len(CJK_RE.findall(text))
    # CJK token estimate: ~1.3 tokens per CJK char for mixed tokenizer, 1.5 for pure
    cjk_tokens = int(cjk_chars * 0.75 + 0.5) + max(1, cjk_chars // 10)  # approx
    # More accurate: use 1 token per 1.5 CJK chars
    cjk_tokens = max(1, round(cjk_chars / 1.35)) if cjk_chars else 0
    whitespace_words = len(re.findall(r'\S+', text)) if text else 0
    return {"cjk_chars": cjk_chars, "cjk_tokens": cjk_tokens, "whitespace_words": whitespace_words, "total_chars": len(text), "text": text[:500]}

def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

class CanonChunk(BaseModel):
    chunk_id: str
    source_id: str = "epub_nhat_the"
    chapter_index: int
    spine_order: int = 0
    chapter_type: str
    title: str
    source_href: str
    text: str
    char_count: int = 0
    word_count: int = 0
    cjk_chars: int = 0
    cjk_tokens: int = 0
    checksum: str = ""
    entities: List[str] = Field(default_factory=list)

class CanonChapterDoc(BaseModel):
    chapter_index: int
    spine_order: int = 0
    chapter_type: str
    title: str
    source_href: str
    raw_text: str
    checksum: str = ""
    cjk_char_count: int = 0
    cjk_tokens: int = 0
    word_count: int = 0
    chunks: List[CanonChunk] = Field(default_factory=list)

INTRO_KEYWORDS = ["制作说明", "版权", "简介", "前言", "内容简介", "作者简介", "扉页"]
# href-based patterns
SIDE_STORY_HREF_RE = re.compile(r'fy|fanwai|番外', re.I)
MAIN_CHAPTER_HREF_RE = re.compile(r'part-\d+-ch\d+', re.I)
MAIN_CHAPTER_TITLE_RE = re.compile(r'第[0-9一二三四五六七八九十百千零〇\d]+章')
# part divider: href like part-01.html / volume01.xhtml with NO chapter number
PART_DIVIDER_HREF_RE = re.compile(r'part-\d+\.x?html?$', re.I)
PART_DIVIDER_TITLE_RE = re.compile(r'^第[一二三四五六七八九十\d]+卷[：: ]')

class SpineAwareEpubParser:
    @staticmethod
    def _find_opf_path(zf: zipfile.ZipFile) -> str:
        try:
            container_bytes = zf.read("META-INF/container.xml")
            root = ET.fromstring(container_bytes)
            for elem in root.iter():
                if elem.tag.endswith("rootfile"):
                    return elem.attrib.get("full-path", "")
        except Exception:
            pass
        for name in zf.namelist():
            if name.endswith(".opf"):
                return name
        return "content.opf"

    @staticmethod
    def _extract_heading_title(html_raw: str) -> str:
        """Extract title from heading elements only (h1-h4, title tag), not prose."""
        m = re.search(r'<title[^>]*>(.*?)</title>', html_raw, re.I|re.DOTALL)
        if m:
            t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if t and len(t) < 120:
                return html.unescape(t)
        for tag in ['h1','h2','h3','h4']:
            m = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', html_raw, re.I|re.DOTALL)
            if m:
                t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                t = html.unescape(t)
                if t and len(t) < 120:
                    return t
        return ""

    @classmethod
    def _classify(cls, href: str, heading_title: str, properties: str = "") -> str:
        href_l = href.lower()
        # 1. Cover
        if "cover" in href_l or "cover-image" in properties:
            return "cover"
        # 2. Side story
        if SIDE_STORY_HREF_RE.search(href_l) or "番外" in heading_title:
            return "side_story"
        # 3. Frontmatter / introduction — only by href or heading, not prose
        if any(k in href_l for k in ["intro", "foreword", "preface", "copyright"]) or any(k in heading_title for k in INTRO_KEYWORDS):
            return "frontmatter"
        if heading_title and any(k in heading_title for k in INTRO_KEYWORDS):
            return "frontmatter"
        # 4. Part divider — href is volume file AND heading indicates 卷 divider
        if PART_DIVIDER_HREF_RE.search(href_l):
            if PART_DIVIDER_TITLE_RE.search(heading_title.strip()):
                return "part_divider"
            # href is volume file but no 卷 heading => still part_divider if no chapter pattern
            if not MAIN_CHAPTER_HREF_RE.search(href_l) and not MAIN_CHAPTER_TITLE_RE.search(heading_title):
                return "part_divider"
        # 5. Main chapter — href pattern OR heading has 第X章
        if MAIN_CHAPTER_HREF_RE.search(href_l):
            return "main_chapter"
        if MAIN_CHAPTER_TITLE_RE.search(heading_title):
            return "main_chapter"
        # Fallback: if href looks like chapter file (contains ch/Chapter) treat as main
        if re.search(r'ch\d+', href_l):
            return "main_chapter"
        return "frontmatter"

    @classmethod
    def parse_epub_spine(cls, epub_path: str, max_items: Optional[int] = None, min_char_length: int = 5) -> List[CanonChapterDoc]:
        if not zipfile.is_zipfile(epub_path):
            raise ValueError(f"Không phải file EPUB hợp lệ: {epub_path}")
        documents: List[CanonChapterDoc] = []
        with zipfile.ZipFile(epub_path, 'r') as zf:
            opf_path = cls._find_opf_path(zf)
            opf_bytes = zf.read(opf_path)
            opf_root = ET.fromstring(opf_bytes)
            opf_dir = str(Path(opf_path).parent)
            if opf_dir == ".": opf_dir = ""
            # manifest: id -> (href, properties)
            manifest: Dict[str, Dict[str,str]] = {}
            for item in opf_root.iter():
                if item.tag.endswith("item"):
                    i_id = item.attrib.get("id", "")
                    i_href = item.attrib.get("href", "")
                    props = item.attrib.get("properties", "")
                    if i_id and i_href:
                        full_href = f"{opf_dir}/{i_href}".lstrip("/") if opf_dir else i_href
                        manifest[i_id] = {"href": full_href, "properties": props}
            # spine order
            spine_order: List[Dict[str,str]] = []
            for itemref in opf_root.iter():
                if itemref.tag.endswith("itemref"):
                    idref = itemref.attrib.get("idref", "")
                    if idref in manifest:
                        spine_order.append(manifest[idref])
            if not spine_order:
                spine_order = [{"href": f, "properties": ""} for f in sorted(zf.namelist()) if f.endswith(('.html','.xhtml','.htm'))]
            chapter_idx = 1
            spine_idx = 0
            for entry in spine_order:
                spine_idx += 1
                if max_items and len(documents) >= max_items:
                    break
                href = entry["href"]
                props = entry.get("properties","")
                try:
                    raw_bytes = zf.read(href)
                    raw_html = raw_bytes.decode('utf-8', errors='ignore')
                    checksum = _sha16(raw_html)
                    heading_title = cls._extract_heading_title(raw_html)
                    ch_type = cls._classify(href, heading_title, props)
                    metrics = cjk_metrics(raw_html)
                    clean_text = metrics["text"]
                    # Use full text for doc
                    full_metrics = cjk_metrics(raw_html)
                    # Re-extract full text properly
                    tmp = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', raw_html, flags=re.DOTALL|re.I)
                    tmp = re.sub(r'<[^>]+>', ' ', tmp)
                    tmp = html.unescape(tmp)
                    tmp = re.sub(r'\s+', ' ', tmp).strip()
                    if len(tmp) < min_char_length:
                        continue
                    # Title fallback
                    title = heading_title if heading_title else (full_metrics["text"][:60] if full_metrics["text"] else f"Mục {chapter_idx}")
                    # For main/side chapters, try to extract 第X章 as title
                    m2 = MAIN_CHAPTER_TITLE_RE.search(tmp[:200])
                    if m2 and ch_type in ("main_chapter","side_story"):
                        title = m2.group(0).strip()[:80]
                    cjk_chars = len(CJK_RE.findall(tmp))
                    cjk_tokens = max(0, round(cjk_chars / 1.35)) if cjk_chars else 0
                    word_count = len(re.findall(r'\S+', tmp))
                    # Chunking: split by sentence boundaries, ~1200 chars per chunk
                    chunks: List[CanonChunk] = []
                    sentences = re.split(r'([。！？\n])', tmp)
                    cur = ""
                    sub_idx = 1
                    for s in sentences:
                        cur += s
                        if len(cur) >= 1200:
                            cc = len(CJK_RE.findall(cur))
                            chunks.append(CanonChunk(
                                chunk_id=f"chunk_ch{chapter_idx:04d}_{sub_idx:03d}",
                                chapter_index=chapter_idx, spine_order=spine_idx,
                                chapter_type=ch_type, title=title, source_href=href,
                                text=cur.strip(), char_count=len(cur.strip()),
                                word_count=len(re.findall(r'\S+', cur.strip())),
                                cjk_chars=cc, cjk_tokens=round(cc/1.35) if cc else 0,
                                checksum=_sha16(cur)
                            ))
                            cur = ""; sub_idx+=1
                    if cur.strip():
                        cc = len(CJK_RE.findall(cur))
                        chunks.append(CanonChunk(
                            chunk_id=f"chunk_ch{chapter_idx:04d}_{sub_idx:03d}",
                            chapter_index=chapter_idx, spine_order=spine_idx,
                            chapter_type=ch_type, title=title, source_href=href,
                            text=cur.strip(), char_count=len(cur.strip()),
                            word_count=len(re.findall(r'\S+', cur.strip())),
                            cjk_chars=cc, cjk_tokens=round(cc/1.35) if cc else 0,
                            checksum=_sha16(cur)
                        ))
                    doc = CanonChapterDoc(
                        chapter_index=chapter_idx, spine_order=spine_idx,
                        chapter_type=ch_type, title=title, source_href=href,
                        raw_text=tmp, checksum=checksum,
                        cjk_char_count=cjk_chars, cjk_tokens=cjk_tokens,
                        word_count=word_count, chunks=chunks
                    )
                    documents.append(doc)
                    chapter_idx+=1
                except KeyError:
                    continue
                except Exception:
                    continue
        return documents


def _extract_entities_with_aliases(text: str) -> list:
    """Extract entities using alias_normalizer (fold-aware) + fallback Chinese names."""
    found = []
    try:
        from fanfic_pipeline.packages.canon.alias_normalizer import get_alias_normalizer
        norm = get_alias_normalizer()
        # Use entity_spans which is fold-aware
        for span in norm.entity_spans(text):
            if span["entity_id"] not in found:
                found.append(span["entity_id"])
    except: pass
    # Also direct registry exact match for CJK (no fold needed)
    try:
        from fanfic_pipeline.packages.canon.alias_registry import AliasRegistry
        reg = AliasRegistry()
        amap = getattr(reg, 'alias_to_entity', {}) or getattr(reg, 'aliases', {}) or {}
        for alias, eid in amap.items():
            if alias and alias in text and (eid not in found):
                found.append(eid if isinstance(eid, str) else alias)
    except: pass
    # Fallback: core Chinese names if not already found
    core_zh = ["孟奇", "江芷微", "顾小桑", "张远山", "齐正言", "阮玉书", "孟奇 (苏孟)", "真定"]
    for name in core_zh:
        if name in text and name not in found:
            found.append(name)
    return list(dict.fromkeys(found))  # dedupe keep order
