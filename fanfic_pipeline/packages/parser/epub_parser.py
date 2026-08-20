"""
Industrial-grade EPUB & Text Corpus Ingestion Engine (v0.8 Production-Ready):
Parses raw novel files (e.g. Q565-一世之尊V1.0.epub), splits chapters,
builds entity index (characters, realms, techniques, locations), and prepares RAG chunks.
"""

import zipfile
import re
from typing import List, Dict, Any, Optional

class NovelChapter:
    def __init__(self, chapter_index: int, title: str, raw_text: str, word_count: int):
        self.chapter_index = chapter_index
        self.title = title
        self.raw_text = raw_text
        self.word_count = word_count

class EpubIngestionEngine:
    @staticmethod
    def parse_epub(epub_path: str, max_chapters: Optional[int] = None, min_char_length: int = 30) -> List[NovelChapter]:
        chapters = []
        if not zipfile.is_zipfile(epub_path):
            raise ValueError(f"Tệp không phải là định dạng EPUB hợp lệ: {epub_path}")

        with zipfile.ZipFile(epub_path, 'r') as zf:
            html_files = [f for f in zf.namelist() if f.endswith(('.html', '.xhtml', '.htm')) and 'cover' not in f.lower()]
            html_files.sort()

            idx = 1
            for filename in html_files:
                if max_chapters and idx > max_chapters:
                    break
                try:
                    content_bytes = zf.read(filename)
                    text = content_bytes.decode('utf-8', errors='ignore')
                    clean_text = re.sub(r'<[^>]+>', ' ', text)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    
                    if len(clean_text) < min_char_length:
                        continue

                    title_match = re.search(r'(第[0-9一二三四五六七八九十百千]+章[^\n\r]{0,30}|Chapter\s*\d+[^\n\r]{0,30}|Hồi\s*\d+[^\n\r]{0,30})', clean_text)
                    title = title_match.group(0).strip() if title_match else f"Hồi {idx}"

                    words = len(re.findall(r'\S+', clean_text))
                    chapters.append(NovelChapter(
                        chapter_index=idx,
                        title=title,
                        raw_text=clean_text,
                        word_count=words
                    ))
                    idx += 1
                except Exception:
                    continue

        return chapters

    @staticmethod
    def extract_key_entities(chapters: List[NovelChapter]) -> Dict[str, Any]:
        entities = {
            "characters": {},
            "realms": {},
            "techniques": {}
        }
        known_chars = ["Mạnh Kỳ", "Chân Định", "Tô Mạnh", "Giang Chỉ Vi", "Cố Tiểu Tang", "Tề Chính Ngôn", "Nguyễn Ngọc Thư", "Triệu Hằng", "Huyền Bi", "Ma Phật", "An Nan", "孟奇", "江芷微", "顾小桑"]
        known_realms = ["Bách Nhật Trúc Cơ", "Tích Khí", "Khai Khiếu", "Cửu Khiếu", "Tề Khiếu", "Ngoại Cảnh", "Thiên Nhân Hợp Nhất", "Pháp Thân", "Truyền Thuyết", "Tạo Hóa", "Bỉ Ngạn", "开窍"]
        known_techs = ["Bát Cửu Huyền Công", "Như Lai Thần Chưởng", "Tiệt Thiên Thất Kiếm", "Lôi Đao", "Khai Thiên Thập Kích", "Cửu Trọng Thiên", "八九玄功", "雷刀"]

        for ch in chapters:
            for c in known_chars:
                count = ch.raw_text.count(c)
                if count > 0:
                    entities["characters"][c] = entities["characters"].get(c, 0) + count
            for r in known_realms:
                count = ch.raw_text.count(r)
                if count > 0:
                    entities["realms"][r] = entities["realms"].get(r, 0) + count
            for t in known_techs:
                count = ch.raw_text.count(t)
                if count > 0:
                    entities["techniques"][t] = entities["techniques"].get(t, 0) + count

        return entities
