"""
Deep 1410-Chapter Raw Text Compiler for the Complete 7-Block Master Lore Pack.
Reads all xhtml chapters from Q565-一世之尊V1.0.epub and enriches all 7 JSON assets.
"""
import os, zipfile, re, json
from collections import defaultdict, Counter

def compile_all_7_packs(epub_path: str = "Q565-一世之尊V1.0.epub"):
    out_dir = "fanfic_pipeline/data/nhat_the_chi_ton"
    os.makedirs(out_dir, exist_ok=True)

    print(f"📖 ĐANG ĐỌC TRỰC TIẾP TOÀN VĂN 1.410 CHƯƠNG TỪ {epub_path}...")

    # Data collectors
    total_chapters = 0
    total_words = 0
    locations = Counter()
    weapons = Counter()
    techniques = Counter()
    characters = defaultdict(lambda: {"mentions": 0, "first_ch": 9999, "last_ch": 0, "quotes": []})

    # Regex patterns
    dialogue_pat = re.compile(r'“([^”]{4,100})”|"([^"]{4,100})"')
    weapon_pat = re.compile(r'[\u4e00-\u9fa5]{2,6}(?:刀|剑|琴|枪|戟|印|钟|塔|镜|幡|图|册|棒|棍|索|鞭|珠|鼎|炉)')
    technique_pat = re.compile(r'[\u4e00-\u9fa5]{2,6}(?:剑法|刀法|神掌|神功|真经|秘典|玄功|心法|神拳|指法|步法|绝技|魔功|雷法|剑诀|刀诀|剑经|琴谱|阵法|秘术|天功|掌法|棍法|枪法|锤法|神指|身法|化诀|奇功|大法)')
    stop_chars = set("的是和了在与他我你之被把各种等门套招门有这那几本所修炼以展开一把一柄一柄柄一把把")

    char_registry = {
        "meng_qi": ("Mạnh Kỳ", ["孟奇", "真定", "苏孟", "苏子远", "狂刀"]),
        "jiang_zhiwei": ("Giang Chỉ Vi", ["江芷微", "芷微"]),
        "gu_xiaosang": ("Cố Tiểu Tang", ["顾小桑", "小桑", "妖女"]),
        "qi_zhengyan": ("Tề Chính Ngôn", ["齐正言", "正言"]),
        "ruan_yushu": ("Nguyễn Ngọc Thư", ["阮玉书", "玉书"]),
        "wang_siyuan": ("Vương Tư Viễn", ["王思远", "算尽苍生"]),
        "su_wuming": ("Tô Vô Danh", ["苏无名"]),
        "he_jiu": ["何九"],
        "duan_xiangfei": ("Đoạn Hướng Phi", ["段向非"]),
        "zhen_hui": ("Chân Tuệ", ["真慧"]),
        "xuan_zhen": ("Huyền Chân", ["玄真"]),
        "an_nan": ("Ma Phật An Nan", ["阿难", "魔佛"]),
        "jin_mu": ("Vô Sinh Lão Mẫu", ["无生老母", "金母"]),
        "tian_di": ("Thiên Đế", ["天帝"]),
        "dao_de": ("Đạo Đức Thiên Tôn", ["道德天尊"]),
        "ling_bao": ("Linh Bảo Thiên Tôn", ["灵宝天尊"]),
        "yuan_shi": ("Nguyên Thủy Thiên Tôn", ["元始天尊"])
    }

    loc_keywords = {
        "Thiếu Lâm Tự (Hà Nam)": ["少林寺", "少林"],
        "Tẩy Kiếm Các (Giang Nam)": ["洗剑阁"],
        "Chân Võ Tông (Võ Đang)": ["真武宗", "真武派"],
        "Huyền Thiên Tông (Trung Nguyên)": ["玄天宗"],
        "Côn Luân Sơn Ngọc Hư Cung": ["昆仑山", "玉虚宫"],
        "Lang Nha Nguyễn Thị (Giang Đông)": ["琅琊", "阮氏"],
        "Thần Đô (Đại Tấn Hoàng Triều)": ["神都", "大晋"],
        "Bắc Hoang Thảo Nguyên": ["北荒", "草原"],
        "Tây Vực Ma Địa": ["西域", "瀚海"],
        "Cửu Trọng Thiên (Thiên Đình)": ["九重天", "天庭"],
        "Cửu U (Ma Giới)": ["九幽", "幽冥"]
    }

    with zipfile.ZipFile(epub_path, "r") as zf:
        html_files = sorted([f for f in zf.namelist() if f.endswith((".html", ".xhtml", ".htm")) and "cover" not in f.lower() and "title" not in f.lower()])
        
        for ch_idx, fname in enumerate(html_files, 1):
            raw = zf.read(fname).decode("utf-8", errors="ignore")
            clean = re.sub(r"<[^>]+>", " ", raw)
            clean = re.sub(r"\s+", " ", clean).strip()
            
            if len(clean) < 50:
                continue
            total_chapters += 1
            total_words += len(re.findall(r"\S+", clean))

            # 1. Môn phái / Địa danh
            for loc_name, keys in loc_keywords.items():
                if any(k in clean for k in keys):
                    locations[loc_name] += 1

            # 2. Binh khí / Pháp bảo
            for w in weapon_pat.findall(clean):
                if 2 <= len(w) <= 6 and not any(c in w for c in stop_chars):
                    weapons[w] += 1

            # 3. Võ học / Công pháp
            for t in technique_pat.findall(clean):
                if 3 <= len(t) <= 7 and not any(c in t for c in stop_chars):
                    techniques[t] += 1

            # 4. Nhân vật & Lời thoại
            for cid, info in char_registry.items():
                cname = info[0] if isinstance(info, tuple) else info
                keys = info[1] if isinstance(info, tuple) else info
                if any(k in clean for k in keys):
                    characters[cid]["mentions"] += 1
                    characters[cid]["first_ch"] = min(characters[cid]["first_ch"], ch_idx)
                    characters[cid]["last_ch"] = max(characters[cid]["last_ch"], ch_idx)
                    if len(characters[cid]["quotes"]) < 5:
                        for match in dialogue_pat.findall(clean):
                            d = match[0] or match[1]
                            pos = clean.find(d)
                            surrounding = clean[max(0, pos-30):pos+len(d)+30]
                            if any(k in surrounding for k in keys):
                                characters[cid]["quotes"].append(f"[Ch.{ch_idx}] “{d}”")
                                break

    print(f"📊 TỔNG HỢP XONG TỪ RAW TEXT:")
    print(f"  - Tổng số chương: {total_chapters}")
    print(f"  - Tổng số từ: {total_words:,}")
    print(f"  - Địa danh xuất hiện: {len(locations)}")
    print(f"  - Thần binh / Binh khí: {len(weapons)}")
    print(f"  - Võ học trích xuất: {len(techniques)}")

    # GHI LẠI 7 PHẦN TRONG MASTER LORE PACK
    # 1. manifest.json
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({
            "fandom_id": "nhat_the_chi_ton",
            "title": "Nhất Thế Chi Tôn",
            "chinese_title": "一世之尊",
            "author": "Ái Tiềm Thủy Đích Ô Tặc",
            "total_canon_chapters": total_chapters,
            "total_canon_words": total_words,
            "version": "2.1.0",
            "power_ceiling": "Đạo Quả (Siêu Thoát)",
            "techniques_mined": len(techniques),
            "weapons_mined": len(weapons)
        }, f, ensure_ascii=False, indent=2)

    # 2. world_geography.json
    with open(os.path.join(out_dir, "world_geography.json"), "w", encoding="utf-8") as f:
        json.dump({
            "top_locations_presence": dict(locations.most_common(15)),
            "travel_times": {
                "Thiếu Lâm -> Lạc Dương": "Khai Khiếu: 3 ngày ngựa; Ngoại Cảnh: 2 canh giờ.",
                "Thần Đô -> Giang Đông": "Khai Khiếu: 7 ngày thuyền/ngựa; Ngoại Cảnh: nửa ngày.",
                "Thần Đô -> Bắc Hoang": "Khai Khiếu: 15 ngày; Ngoại Cảnh: 1 ngày.",
                "Chân Thực Giới -> Cửu Trọng Thiên": "Cần mở thông đạo Cửu Trọng Thiên hoặc dùng Lôi Đao phá giới."
            }
        }, f, ensure_ascii=False, indent=2)

    # 3. cultivation_mechanics.json
    with open(os.path.join(out_dir, "cultivation_mechanics.json"), "w", encoding="utf-8") as f:
        json.dump({
            "top_mined_techniques": dict(techniques.most_common(120)),
            "top_mined_weapons": dict(weapons.most_common(50)),
            "realms_26_tiers": [
                {"rank": 0, "name": "Bách Nhật Trúc Cơ"},
                {"rank": 1, "name": "Thiền Định Súc Khí"},
                {"rank": 2, "name": "Khai Khiếu (1-4 Khiếu: Mắt, Tai, Mũi)"},
                {"rank": 3, "name": "Khai Khiếu (5-7 Khiếu: Miệng, Tiền Âm, Hậu Âm)"},
                {"rank": 4, "name": "Khai Khiếu (8-9 Khiếu: Cửu Khiếu Tề Khai)"},
                {"rank": 5, "name": "Bán Bộ Ngoại Cảnh (Thiên Nhân Hợp Nhất)"},
                {"rank": 6, "name": "Ngoại Cảnh (1-3 Trọng Thiên - Sơ kỳ)"},
                {"rank": 7, "name": "Ngoại Cảnh (4-6 Trọng Thiên - Trung kỳ)"},
                {"rank": 8, "name": "Ngoại Cảnh (7 Trọng Thiên - Tông Sư)"},
                {"rank": 9, "name": "Ngoại Cảnh (8 Trọng Thiên - Đại Tông Sư)"},
                {"rank": 10, "name": "Ngoại Cảnh (9 Trọng Thiên - Đỉnh Phong)"},
                {"rank": 11, "name": "Bán Bộ Pháp Thân"},
                {"rank": 12, "name": "Pháp Thân (Nhân Tiên)"},
                {"rank": 13, "name": "Pháp Thân (Địa Tiên)"},
                {"rank": 14, "name": "Pháp Thân (Thiên Tiên)"},
                {"rank": 15, "name": "Truyền Thuyết Cảnh (Thần Tiên)"},
                {"rank": 16, "name": "Tạo Hóa Cảnh (Kim Tiên / Thái Ất)"},
                {"rank": 17, "name": "Bỉ Ngạn Cảnh (Đại La / Hỗn Nguyên)"},
                {"rank": 18, "name": "Đạo Quả (Siêu Thoát)"}
            ]
        }, f, ensure_ascii=False, indent=2)

    # 4. factions_and_conspiracies.json
    with open(os.path.join(out_dir, "factions_and_conspiracies.json"), "w", encoding="utf-8") as f:
        json.dump({
            "factions": {
                "Thiếu Lâm Tự": "Đệ nhất Phật môn (Phương trượng Không Văn, Huyền Bi, Chân Định/Mạnh Kỳ).",
                "Tẩy Kiếm Các": "Đệ nhất kiếm phái (Tô Vô Danh, Giang Chỉ Vi).",
                "Chân Võ Tông": "Đạo môn chính tông (Trương Tam Phong truyền thừa).",
                "Huyền Thiên Tông": "Thiên Đế truyền thừa, Thời Gian Chi Đao.",
                "Tố Nữ Đạo": "Lục Đại Ma Môn (Cố Tiểu Tang, Vô Sinh Lão Mẫu).",
                "Diệt Thiên Môn": "Diệt Thiên Ma Đao sát phạt.",
                "Lang Nha Nguyễn Thị": "Cầm đạo âm luật (Nguyễn Ngọc Thư)."
            },
            "masterminds": {
                "Ma Phật An Nan": "Chủ mưu Lục Đạo, biến Mạnh Kỳ thành đạo tiêu trùng sinh.",
                "Vô Sinh Lão Mẫu": "Bỉ Ngạn đại năng, khống chế Cố Tiểu Tang.",
                "Tam Thanh": "Nguyên Thủy, Linh Bảo, Đạo Đức - Bố cục Mạnh Kỳ gánh vác nhân quả siêu thoát."
            }
        }, f, ensure_ascii=False, indent=2)

    # 5. canonical_timeline.json
    with open(os.path.join(out_dir, "canonical_timeline.json"), "w", encoding="utf-8") as f:
        json.dump({
            "grand_arcs": [
                {"arc": 1, "chapters": "1-50", "title": "Tân Thủ Luân Hồi & Thiếu Lâm Tàng Kinh", "core_events": "Nhập Thiếu Lâm, Ẩn Hình Phường, kết bạn Chỉ Vi."},
                {"arc": 2, "chapters": "51-150", "title": "Giang Hồ Sơ Xuất & Nhân Bảng Tranh Phong", "core_events": "Cuồng Đao Tô Mạnh, Huyễn Hình Đại Pháp, gặp Tiểu Tang."},
                {"arc": 3, "chapters": "151-300", "title": "Cửu Trọng Thiên & Lôi Đao Nhận Chủ", "core_events": "Đột phá Cửu Khiếu, Tề Chính Ngôn nhận Ma Hoàng truyền thừa."},
                {"arc": 4, "chapters": "301-500", "title": "Đại Biến Thiếu Lâm & Xuất Sư Hoàn Tục", "core_events": "Thân thế Tô Tử Viễn bại lộ, trảm đoạn Thiếu Lâm, chứng Ngoại Cảnh."},
                {"arc": 5, "chapters": "501-800", "title": "Tiên Sinh Tóc Bạc & Nỗi Hận 10 Năm", "core_events": "Tiểu Tang tự sát tuyệt mạng Kim Mẫu, Mạnh Kỳ tóc bạc ôm hận."},
                {"arc": 6, "chapters": "801-1100", "title": "Chứng Đạo Pháp Thân & Ngọc Hư Chưởng Giáo", "core_events": "Chứng Bất Diệt Nguyên Thủy Pháp Thân, phục sinh Tiểu Tang."},
                {"arc": 7, "chapters": "1101-1409", "title": "Mạt Thế Đại Kiếp & Bỉ Ngạn Tranh Đạo Quả", "core_events": "Đăng lâm Bỉ Ngạn, trảm sát Ma Phật, chứng Đạo Quả siêu thoát."}
            ]
        }, f, ensure_ascii=False, indent=2)

    # 6. character_dossiers.json
    dossiers = {}
    for cid, data in characters.items():
        cname = char_registry[cid][0] if isinstance(char_registry[cid], tuple) else char_registry[cid]
        dossiers[cid] = {
            "name": cname,
            "first_seen_chapter": data["first_ch"] if data["first_ch"] != 9999 else 1,
            "last_seen_chapter": data["last_ch"],
            "total_mentions": data["mentions"],
            "sample_dialogues": data["quotes"]
        }
    with open(os.path.join(out_dir, "character_dossiers.json"), "w", encoding="utf-8") as f:
        json.dump({"characters": dossiers}, f, ensure_ascii=False, indent=2)

    # 7. cosmic_invariants.json
    with open(os.path.join(out_dir, "cosmic_invariants.json"), "w", encoding="utf-8") as f:
        json.dump({
            "invariants": [
                "Luật Lục Đạo: Cấm tiết lộ bí mật Lục Đạo cho người chưa vào Luân Hồi.",
                "Luật Nhân Quả: Công pháp Bỉ Ngạn mang nhân quả sâu nặng.",
                "Luật Thời Gian: Quá khứ không thể tùy tiện sửa đổi nếu không có thực lực Bỉ Ngạn.",
                "Luật Khai Khiếu: Phải mở đủ 9 khiếu mới có thể tiến hành Thiên Nhân Giao Cảm."
            ]
        }, f, ensure_ascii=False, indent=2)

    print(f"🎉 HOÀN TẤT BỔ SUNG TRỌN VẸN 7 PHẦN MASTER LORE PACK VÀO {out_dir}/!")

if __name__ == "__main__":
    compile_all_7_packs()
