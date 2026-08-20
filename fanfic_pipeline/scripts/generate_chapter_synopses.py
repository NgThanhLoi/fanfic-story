"""
Generates chapter-by-chapter (1 to 1410) episodic summaries from EPUB
so a zero-knowledge writer has the complete chapter-level roadmap.
"""
import os, zipfile, re, json

def generate_synopses(epub_path: str = "Q565-一世之尊V1.0.epub"):
    out_file = "fanfic_pipeline/data/nhat_the_chi_ton/chapter_synopses_1410.json"
    synopses = []

    with zipfile.ZipFile(epub_path, "r") as zf:
        html_files = sorted([f for f in zf.namelist() if f.endswith((".html", ".xhtml", ".htm")) and "cover" not in f.lower() and "title" not in f.lower()])
        
        for idx, fname in enumerate(html_files, 1):
            raw = zf.read(fname).decode("utf-8", errors="ignore")
            clean = re.sub(r"<[^>]+>", " ", raw)
            clean = re.sub(r"\s+", " ", clean).strip()
            
            if len(clean) < 50:
                continue
                
            title_m = re.search(r'(第[0-9一二三四五六七八九十百千]+章[^\s\n\r]{0,30})', clean)
            title = title_m.group(0).strip() if title_m else f"Chương {idx}"
            
            # Extract first 2-3 significant sentences for synopsis
            sentences = [s.strip() for s in re.split(r'[。！？\n]', clean) if len(s.strip()) > 8]
            sample_summary = "。".join(sentences[:2]) + "。" if sentences else clean[:120]
            
            synopses.append({
                "chapter": idx,
                "title": title,
                "summary": sample_summary[:160]
            })

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(synopses, f, ensure_ascii=False, indent=2)

    print(f"✅ ĐÃ TẠO XONG TÓM TẮT TỪNG CHƯƠNG (1..{len(synopses)}) TẠI {out_file}")

if __name__ == "__main__":
    generate_synopses()
