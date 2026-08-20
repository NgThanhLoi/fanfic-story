"""
Story Bible Generator: Compiles multi-volume, multi-arc hierarchical story bibles from enriched window summaries.
"""
import json, pathlib
from typing import List, Dict, Any, Optional
from fanfic_pipeline.packages.enrichment.enrichment_store import ArcSummaryRecord

def generate_macro_bible_v2(
    arc_summaries: List[ArcSummaryRecord],
    total_chapters: int = 1000,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    volumes = [
        {
            "volume_id": "vol_01",
            "volume_number": 1,
            "title": "Quyển 1: Thiếu Lâm Tân Thủ & Luân Hồi Sơ Khởi",
            "chapter_range": [1, 150],
            "theme": "Sống sót và trưởng thành qua các nhiệm vụ Luân Hồi sơ cấp",
            "main_antagonist": "Ma Môn tà tu & sát thủ Ẩn Hình Phường",
            "realm_milestone": "Khai Khiếu cửu khiếu viên mãn",
            "active_arcs": ["arc_01", "arc_02", "arc_03", "arc_04"]
        },
        {
            "volume_id": "vol_02",
            "volume_number": 2,
            "title": "Quyển 2: Giang Hồ Phong Vân & Danh Chấn Cửu Châu",
            "chapter_range": [151, 350],
            "theme": "Bôn tẩu giang hồ, tranh đoạt Nhân Bảng và Ngoại Cảnh đại kiếp",
            "main_antagonist": "Bắc Địch cao thủ & Tà ma cửu đạo",
            "realm_milestone": "Đột phá Ngoại Cảnh (Thiên Nhân Hợp Nhất)",
            "active_arcs": ["arc_05", "arc_06", "arc_07", "arc_08"]
        },
        {
            "volume_id": "vol_03",
            "volume_number": 3,
            "title": "Quyển 3: Thần Đô Tranh Bá & Pháp Thân Chi Lộ",
            "chapter_range": [351, 600],
            "theme": "Vương triều tranh đoạt, pháp thân kiếp nạn và khám phá chân tướng Luân Hồi",
            "main_antagonist": "Hàn Quảng (Ma Hoàng) & Triệu Vô Ngôn",
            "realm_milestone": "Chứng đạo Pháp Thân (Địa Tiên)",
            "active_arcs": ["arc_09", "arc_10", "arc_11", "arc_12"]
        },
        {
            "volume_id": "vol_04",
            "volume_number": 4,
            "title": "Quyển 4: Vạn Cổ Cục Diện & Bỉ Ngạn Siêu Thoát",
            "chapter_range": [601, total_chapters],
            "theme": "Đối đầu Chư Thiên Đại Năng, chặt đứt nhân quả Ma Phật An Nan",
            "main_antagonist": "Ma Phật An Nan & Lục Đạo Chi Chủ",
            "realm_milestone": "Đăng lâm Bỉ Ngạn Cảnh",
            "active_arcs": ["arc_13", "arc_14", "arc_15", "arc_16"]
        }
    ]

    # Generate fine-grained Story Arcs across all windows
    arcs = {}
    arc_idx = 1
    for i in range(1, total_chapters + 1, 30):
        arc_id = f"arc_{arc_idx:02d}"
        start_c = i
        end_c = min(i + 29, total_chapters)
        
        # Match with enriched summary if available
        matched_summary = next((s for s in arc_summaries if s.start_chapter <= start_c <= s.end_chapter), None)
        title = f"Giai đoạn {arc_idx}: Thử Luyện Chương {start_c}-{end_c}"
        obj = "Vượt qua thử thách và tích lũy thiện công"
        if matched_summary:
            title = f"Chiến Dịch Ch.{start_c}-{end_c}: {matched_summary.summary_text[:40]}"
            obj = matched_summary.summary_text

        arcs[arc_id] = {
            "arc_id": arc_id,
            "title": title,
            "start_chapter": start_c,
            "end_chapter": end_c,
            "objective": obj,
            "turning_points": [
                f"Chương {start_c + 5}: Biến cố khởi phát",
                f"Chương {start_c + 15}: Đối đầu then chốt",
                f"Chương {end_c}: Đột phá và thu hoạch"
            ]
        }
        arc_idx += 1

    macro_bible_v2 = {
        "version": "2.0",
        "volumes": volumes,
        "arcs": arcs,
        "total_chapters": total_chapters
    }

    if output_path:
        pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(output_path).write_text(json.dumps(macro_bible_v2, ensure_ascii=False, indent=2), encoding="utf-8")

    return macro_bible_v2
