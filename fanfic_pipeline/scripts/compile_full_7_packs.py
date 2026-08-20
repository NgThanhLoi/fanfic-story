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

    total_chapters = 0
    total_words = 0
    locations = Counter()
    weapons = Counter()
    techniques = Counter()
    characters = defaultdict(lambda: {"mentions": 0, "first_ch": 9999, "last_ch": 0, "quotes": []})

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
        "an_nan": ("Ma Phật An Nan", ["阿难", "魔佛"])
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

            for loc_name, keys in loc_keywords.items():
                if any(k in clean for k in keys):
                    locations[loc_name] += 1

            for w in weapon_pat.findall(clean):
                if 2 <= len(w) <= 6 and not any(c in w for c in stop_chars):
                    weapons[w] += 1

            for t in technique_pat.findall(clean):
                if 3 <= len(t) <= 7 and not any(c in t for c in stop_chars):
                    techniques[t] += 1

            for cid, (cname, keys) in char_registry.items():
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
            "realms": {
                "Chân Thực Giới": "Thế giới bản nguyên trung tâm chư thiên. Gồm Đại Tấn, Bắc Hoang, Tây Vực, Nam Hoang, Đông Hải.",
                "Cửu Trọng Thiên": "Di tích Thiên Đình cổ đại của Thiên Đế.",
                "Cửu U": "Thế giới ma đạo u ám của Ma Hoàng và Huyết Hải.",
                "Côn Luân Sơn Ngọc Hư Cung": "Đạo tràng cổ xưa của Nguyên Thủy Thiên Tôn."
            },
            "travel_mechanics": {
                "Bách Nhật Trúc Cơ / Súc Khí": "Đi bộ hoặc xe ngựa (20-40 dặm/ngày).",
                "Khai Khiếu (1-9 khiếu)": "Khinh công tuyệt đỉnh hoặc ngựa quý (100-300 dặm/ngày).",
                "Ngoại Cảnh (Thiên Nhân Hợp Nhất)": "Ngự phong phi hành, vượt ngàn dặm trong vài canh giờ.",
                "Pháp Thân (Nhân Tiên -> Thiên Tiên)": "Xé rách hư không, di chuyển tức thời.",
                "Bỉ Ngạn": "Vượt thoát dòng thời gian, vô sở bất tại."
            },
            "top_locations_presence": dict(locations.most_common(15))
        }, f, ensure_ascii=False, indent=2)

    # 3. cultivation_mechanics.json
    realms_26 = [
        {"rank": 0, "name": "Bách Nhật Trúc Cơ", "desc": "Rèn luyện gân cốt khí huyết, đúc nền cơ thể."},
        {"rank": 1, "name": "Thiền Định Súc Khí", "desc": "Tụ khí đan điền, đả thông kỳ kinh bát mạch."},
        {"rank": 2, "name": "Khai Khiếu (Sơ kỳ - 1-4 Khiếu)", "desc": "Khai mở Mắt, Tai, Mũi."},
        {"rank": 3, "name": "Khai Khiếu (Trung kỳ - 5-7 Khiếu)", "desc": "Khai mở Miệng, Tiền Âm, Hậu Âm."},
        {"rank": 4, "name": "Khai Khiếu (Hậu kỳ - 8-9 Khiếu)", "desc": "Khai mở đầy đủ 9 khiếu cơ thể."},
        {"rank": 5, "name": "Khai Khiếu (Cửu Khiếu Tề Khai - Viên Mãn)", "desc": "Nội khí viên mãn, chuẩn bị Thiên Nhân Giao Cảm."},
        {"rank": 6, "name": "Bán Bộ Ngoại Cảnh (Thiên Nhân Hợp Nhất)", "desc": "Nội cảnh sơ thành, cảm ứng hòa nhập cùng thiên địa."},
        {"rank": 7, "name": "Ngoại Cảnh (Nhất Trọng Thiên)", "desc": "Bắt đầu dẫn động thiên địa nguyên khí."},
        {"rank": 8, "name": "Ngoại Cảnh (Nhị Trọng Thiên)", "desc": "Nguyên khí ngưng tụ, uy lực tăng gấp bội."},
        {"rank": 9, "name": "Ngoại Cảnh (Tam Trọng Thiên)", "desc": "Sơ bộ chưởng khống thiên địa quy tắc."},
        {"rank": 10, "name": "Ngoại Cảnh (Tứ Trọng Thiên)", "desc": "Ngoại Cảnh trung giai, ngự không phi hành thuần thục."},
        {"rank": 11, "name": "Ngoại Cảnh (Ngũ Trọng Thiên)", "desc": "Hóa sinh dị tượng thiên địa."},
        {"rank": 12, "name": "Ngoại Cảnh (Lục Trọng Thiên)", "desc": "Đỉnh phong trung giai, sát chiêu toái sơn đoạn giang."},
        {"rank": 13, "name": "Ngoại Cảnh (Thất Trọng Thiên - Tông Sư)", "desc": "Danh xưng Tông Sư võ lâm, độc bộ giang hồ."},
        {"rank": 14, "name": "Ngoại Cảnh (Bát Trọng Thiên - Đại Tông Sư)", "desc": "Danh xưng Đại Tông Sư, trụ cột các đại thế lực."},
        {"rank": 15, "name": "Ngoại Cảnh (Cửu Trọng Thiên - Đỉnh Phong)", "desc": "Chạm tới ngưỡng cửa Pháp Thân."},
        {"rank": 16, "name": "Bán Bộ Pháp Thân", "desc": "Nội cảnh diễn biến động thiên, chuẩn bị độ kiếp."},
        {"rank": 17, "name": "Pháp Thân (Nhân Tiên)", "desc": "Thoát phàm nhập thánh, ngưng tụ Pháp Thân sơ giai."},
        {"rank": 18, "name": "Pháp Thân (Địa Tiên)", "desc": "Địa Tiên cảnh giới, thọ nguyên ngàn năm."},
        {"rank": 19, "name": "Pháp Thân (Thiên Tiên)", "desc": "Thiên Tiên chí tôn, xé rách hư không chư thiên."},
        {"rank": 20, "name": "Bán Bộ Truyền Thuyết", "desc": "Bắt đầu cảm ứng hình chiếu vạn giới."},
        {"rank": 21, "name": "Truyền Thuyết Cảnh", "desc": "Vô Sở Bất Tri, hình chiếu khắp vạn giới (Thần Tiên)."},
        {"rank": 22, "name": "Tạo Hóa Cảnh", "desc": "Khổ hải trầm luân, cải tạo chư thiên (Kim Tiên / Thái Ất)."},
        {"rank": 23, "name": "Bán Bộ Bỉ Ngạn", "desc": "Chạm tới bờ bên kia dòng thời gian."},
        {"rank": 24, "name": "Bỉ Ngạn Cảnh", "desc": "Đứng trên dòng thời gian, hồi tố quá khứ (Đại La / Hỗn Nguyên)."},
        {"rank": 25, "name": "Đạo Quả (Siêu Thoát)", "desc": "Vượt thoát tất cả, chân chính bất khả tư nghị."}
    ]
    with open(os.path.join(out_dir, "cultivation_mechanics.json"), "w", encoding="utf-8") as f:
        json.dump({
            "realms_26_tiers": realms_26,
            "top_mined_techniques": dict(techniques.most_common(120)),
            "top_mined_weapons": dict(weapons.most_common(50))
        }, f, ensure_ascii=False, indent=2)

    # 4. factions_and_conspiracies.json
    with open(os.path.join(out_dir, "factions_and_conspiracies.json"), "w", encoding="utf-8") as f:
        json.dump({
            "chinh_dao": {
                "Thiếu Lâm Tự": "Đệ nhất Phật môn (Phương trượng Không Văn, Huyền Bi, Chân Định/Mạnh Kỳ).",
                "Tẩy Kiếm Các": "Đệ nhất kiếm phái (Tô Vô Danh, Giang Chỉ Vi).",
                "Chân Võ Tông": "Đạo môn chính tông (Trương Tam Phong truyền thừa).",
                "Huyền Thiên Tông": "Thiên Đế truyền thừa, Thời Gian Chi Đao.",
                "Lang Nha Nguyễn Thị": "Cầm đạo âm luật (Nguyễn Ngọc Thư)."
            },
            "ma_mon": {
                "Tố Nữ Đạo": "Lục Đại Ma Môn (Cố Tiểu Tang, Vô Sinh Lão Mẫu).",
                "Diệt Thiên Môn": "Diệt Thiên Ma Đao sát phạt.",
                "Hoan Hỷ Thiền": "Tà Thiền bí thuật, âm dương thải bổ.",
                "Huyết Hải Giáo": "U Minh Huyết Hải, Hóa Huyết Thần Đao."
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
                {"arc_num": 1, "chapters": "1-50", "title": "Tân Thủ Luân Hồi & Thiếu Lâm Tàng Kinh", "mastermind": "Ma Phật An Nan", "core_events": "Nhập Thiếu Lâm, Ẩn Hình Phường, kết bạn Chỉ Vi."},
                {"arc_num": 2, "chapters": "51-150", "title": "Giang Hồ Sơ Xuất & Nhân Bảng Tranh Phong", "mastermind": "Lục Đạo & Lục Đại Ma Môn", "core_events": "Cuồng Đao Tô Mạnh, Huyễn Hình Đại Pháp, gặp Tiểu Tang."},
                {"arc_num": 3, "chapters": "151-300", "title": "Cửu Trọng Thiên & Lôi Đao Nhận Chủ", "mastermind": "Thiên Đế tàn niệm", "core_events": "Đột phá Cửu Khiếu, Tề Chính Ngôn nhận Ma Hoàng truyền thừa."},
                {"arc_num": 4, "chapters": "301-500", "title": "Đại Biến Thiếu Lâm & Xuất Sư Hoàn Tục", "mastermind": "Ma Phật & Huyền Bi", "core_events": "Thân thế Tô Tử Viễn bại lộ, trảm đoạn Thiếu Lâm, chứng Ngoại Cảnh."},
                {"arc_num": 5, "chapters": "501-800", "title": "Tiên Sinh Tóc Bạc & Nỗi Hận 10 Năm", "mastermind": "Kim Mẫu / Vô Sinh Lão Mẫu", "core_events": "Tiểu Tang tự sát tuyệt mạng Kim Mẫu, Mạnh Kỳ tóc bạc ôm hận."},
                {"arc_num": 6, "chapters": "801-1100", "title": "Chứng Đạo Pháp Thân & Ngọc Hư Chưởng Giáo", "mastermind": "Nguyên Thủy Thiên Tôn", "core_events": "Chứng Bất Diệt Nguyên Thủy Pháp Thân, phục sinh Tiểu Tang."},
                {"arc_num": 7, "chapters": "1101-1409", "title": "Mạt Thế Đại Kiếp & Bỉ Ngạn Tranh Đạo Quả", "mastermind": "Tam Thanh & Ma Phật", "core_events": "Đăng lâm Bỉ Ngạn, trảm sát Ma Phật, chứng Đạo Quả siêu thoát."}
            ]
        }, f, ensure_ascii=False, indent=2)

    # 6. character_dossiers.json
    dossiers = {
        "meng_qi": {
            "name": "Mạnh Kỳ",
            "aliases": ["Chân Định", "Cuồng Đao Tô Mạnh", "Tô Tử Viễn", "Tiểu Hòa Thượng", "Tô Tiên Sinh", "Ngọc Hư Chưởng Giáo"],
            "gender": "Nam",
            "first_seen_chapter": characters["meng_qi"]["first_ch"],
            "total_mentions": characters["meng_qi"]["mentions"],
            "stages": {
                "stage_1": {"chapters": "1-50", "title": "Chân Định", "tone": "Dí dỏm, sợ chết, lươn lẹo, thích trang bức."},
                "stage_2": {"chapters": "51-200", "title": "Cuồng Đao Tô Mạnh", "tone": "Hào sảng, ngạo khí, đao ý cuồng bạo."},
                "stage_3": {"chapters": "201-800", "title": "Tô Tiên Sinh", "tone": "Lãnh đạm, trầm mặc, tóc bạc mang hận báo thù."},
                "stage_4": {"chapters": "801-1409", "title": "Ngọc Hư Chưởng Giáo", "tone": "Uy nghiêm, thấu triệt nhân quả, chấp chưởng Côn Luân."}
            },
            "sample_dialogues": characters["meng_qi"]["quotes"]
        },
        "jiang_zhiwei": {
            "name": "Giang Chỉ Vi",
            "aliases": ["Chỉ Vi muội muội", "Kiếm Xuất Vô Hối", "Tẩy Kiếm Các đệ tử"],
            "gender": "Nữ",
            "first_seen_chapter": characters["jiang_zhiwei"]["first_ch"],
            "total_mentions": characters["jiang_zhiwei"]["mentions"],
            "personality": "Kiếm tâm thuần túy, hào sảng hiệp khí, kiếm xuất vô hối, chỗ dựa sinh tử của đồng đội.",
            "sample_dialogues": characters["jiang_zhiwei"]["quotes"]
        },
        "gu_xiaosang": {
            "name": "Cố Tiểu Tang",
            "aliases": ["Tiểu Tang", "Tố Nữ Đạo Thánh Nữ", "Yêu Nữ"],
            "gender": "Nữ",
            "first_seen_chapter": characters["gu_xiaosang"]["first_ch"],
            "total_mentions": characters["gu_xiaosang"]["mentions"],
            "personality": "Thông minh giảo hoạt, miệng gọi 'Tướng công', tâm cơ thâm sâu giấu kín nỗi tuyệt vọng chống lại Kim Mẫu.",
            "sample_dialogues": characters["gu_xiaosang"]["quotes"]
        },
        "qi_zhengyan": {
            "name": "Tề Chính Ngôn",
            "aliases": ["Tề sư huynh", "Mặt đơ", "Ma Hoàng truyền nhân"],
            "gender": "Nam",
            "first_seen_chapter": characters["qi_zhengyan"]["first_ch"],
            "total_mentions": characters["qi_zhengyan"]["mentions"],
            "personality": "Mặt lạnh ít nói, lý tưởng chúng sinh bình đẳng, cam chịu tiếng xấu Ma đạo để cứu giúp phàm nhân."
        },
        "ruan_yushu": {
            "name": "Nguyễn Ngọc Thư",
            "aliases": ["Ngọc Thư", "Lang Nha Nguyễn Thị"],
            "gender": "Nữ",
            "first_seen_chapter": characters["ruan_yushu"]["first_ch"],
            "total_mentions": characters["ruan_yushu"]["mentions"],
            "personality": "Thanh nhã như tiên, bên ngoài lãnh đạm nhưng mê đồ ăn vặt, tiếng đàn Phượng Tê bảo hộ đồng đội."
        }
    }
    with open(os.path.join(out_dir, "character_dossiers.json"), "w", encoding="utf-8") as f:
        json.dump({"characters": dossiers}, f, ensure_ascii=False, indent=2)

    # 7. cosmic_invariants.json
    with open(os.path.join(out_dir, "cosmic_invariants.json"), "w", encoding="utf-8") as f:
        json.dump({
            "taboos": [
                "Luật Lục Đạo: Cấm tiết lộ bí mật Lục Đạo cho người chưa vào Luân Hồi (vi phạm bị xóa sổ).",
                "Luật Nhân Quả: Công pháp Bỉ Ngạn mang nhân quả sâu nặng, không thể tùy tiện tu luyện.",
                "Luật Thời Gian: Quá khứ không thể tùy tiện sửa đổi nếu không có thực lực Bỉ Ngạn.",
                "Luật Khai Khiếu: Phải mở đủ 9 khiếu mới có thể tiến hành Thiên Nhân Giao Cảm."
            ]
        }, f, ensure_ascii=False, indent=2)

    print(f"🎉 HOÀN TẤT BỔ SUNG ĐỒNG BỘ 7 PHẦN MASTER LORE PACK VÀO {out_dir}/!")

if __name__ == "__main__":
    compile_all_7_packs()
