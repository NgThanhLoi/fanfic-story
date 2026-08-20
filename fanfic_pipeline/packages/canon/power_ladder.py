"""
P1.5 — Power Ladder: Comprehensive Cultivation Hierarchy for Nhất Thế Chi Tôn (1409 chapters).
Includes all sub-tiers (Trúc Cơ -> Bỉ Ngạn -> Đạo Quả) and transition plausibility checks.
"""
from typing import List, Dict, Tuple, Optional
from fanfic_pipeline.packages.canon.alias_normalizer import normalize_fold

REALM_ORDER = [
    # Giai đoạn 1: Hậu thiên / Trúc cơ
    "Bách Nhật Trúc Cơ",
    "Tích Khí Kỳ",
    # Giai đoạn 2: Khai Khiếu (1-9 khiếu)
    "Khai Khiếu (Sơ kỳ - 1-4 Khiếu)",
    "Khai Khiếu (Trung kỳ - 5-7 Khiếu)",
    "Khai Khiếu (Hậu kỳ - 8-9 Khiếu)",
    "Khai Khiếu (Cửu Khiếu Tề Khai - Viên Mãn)",
    # Giai đoạn 3: Bán Bộ & Ngoại Cảnh sơ giai
    "Bán Bộ Ngoại Cảnh (Thiên Nhân Hợp Nhất)",
    "Ngoại Cảnh (Nhất Trọng Thiên)",
    "Ngoại Cảnh (Nhị Trọng Thiên)",
    "Ngoại Cảnh (Tam Trọng Thiên)",
    # Giai đoạn 4: Ngoại Cảnh trung giai
    "Ngoại Cảnh (Tứ Trọng Thiên)",
    "Ngoại Cảnh (Ngũ Trọng Thiên)",
    "Ngoại Cảnh (Lục Trọng Thiên)",
    # Giai đoạn 5: Ngoại Cảnh cao giai / Tông Sư / Đại Tông Sư
    "Ngoại Cảnh (Thất Trọng Thiên - Tông Sư)",
    "Ngoại Cảnh (Bát Trọng Thiên - Đại Tông Sư)",
    "Ngoại Cảnh (Cửu Trọng Thiên - Đỉnh Phong)",
    "Bán Bộ Pháp Thân",
    # Giai đoạn 6: Pháp Thân
    "Pháp Thân (Nhân Tiên)",
    "Pháp Thân (Địa Tiên)",
    "Pháp Thân (Thiên Tiên)",
    # Giai đoạn 7: Cảnh giới Đại Năng / Bỉ Ngạn
    "Bán Bộ Truyền Thuyết",
    "Truyền Thuyết Cảnh",
    "Tạo Hóa Cảnh",
    "Bán Bộ Bỉ Ngạn",
    "Bỉ Ngạn Cảnh",
    "Đạo Quả (Siêu Thoát)"
]

RANK = {r: i for i, r in enumerate(REALM_ORDER)}

def rank_of(realm: str) -> int:
    if not realm:
        return -1
    if realm in RANK:
        return RANK[realm]
    norm_target = normalize_fold(realm)
    for k, v in RANK.items():
        norm_k = normalize_fold(k)
        if norm_k in norm_target or norm_target in norm_k:
            return v
    # Substring heuristic
    if "truc co" in norm_target: return 0
    if "tich khi" in norm_target: return 1
    if "khai khieu" in norm_target:
        if "vien man" in norm_target or "cuu khieu" in norm_target: return 5
        if "hau ky" in norm_target: return 4
        if "trung ky" in norm_target: return 3
        return 2
    if "ban bo ngoai canh" in norm_target or "thien nhan hop nhat" in norm_target: return 6
    if "ngoai canh" in norm_target:
        if "cuu trong thien" in norm_target or "dinh phong" in norm_target: return 15
        if "bat trong thien" in norm_target or "dai tong su" in norm_target: return 14
        if "that trong thien" in norm_target or "tong su" in norm_target: return 13
        if "luc trong thien" in norm_target: return 12
        if "ngu trong thien" in norm_target: return 11
        if "tu trong thien" in norm_target: return 10
        if "tam trong thien" in norm_target: return 9
        if "nhi trong thien" in norm_target: return 8
        if "nhat trong thien" in norm_target: return 7
        return 7
    if "ban bo phap than" in norm_target: return 16
    if "phap than" in norm_target:
        if "thien tien" in norm_target: return 19
        if "dia tien" in norm_target: return 18
        return 17
    if "truyen thuyet" in norm_target: return 21
    if "tao hoa" in norm_target: return 22
    if "bi ngan" in norm_target: return 24
    if "dao qua" in norm_target: return 25
    return -1

def plausible(realm_change: str, elapsed_days: int) -> bool:
    """Kiểm tra bước nhảy cảnh giới có hợp lý với khoảng thời gian không."""
    if "->" in realm_change:
        src, dst = [x.strip() for x in realm_change.split("->", 1)]
        r_src = rank_of(src)
        r_dst = rank_of(dst)
        if r_src >= 0 and r_dst >= 0:
            dr = r_dst - r_src
            # Cải lùi cảnh giới lớn mà không có lý do trọng thương/tán công
            if dr < 0 and dr <= -3:
                return False
            # Nhảy vọt quá nhanh
            if dr >= 2 and elapsed_days < 14:
                return False
            if dr >= 4 and elapsed_days < 60:
                return False
            if dr >= 6 and elapsed_days < 180:
                return False
    return True

def can_fly(realm: str) -> bool:
    """Chỉ Ngoại Cảnh trở lên (rank >= 6) mới có thể ngự không phi hành."""
    return rank_of(realm) >= 6
