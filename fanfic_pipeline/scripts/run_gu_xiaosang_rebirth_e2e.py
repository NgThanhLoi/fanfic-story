"""
E2E Fanfic Writer Runner with deepseek-v4-flash-free proxy.
ĐÚNG CHUẨN NGUYÊN TÁC 20 CHƯƠNG ĐẦU:
- Mạnh Kỳ: Tiểu hòa thượng Chân Định tại Thiếu Lâm (Thiền Tâm Viện, Chân Tuệ).
- Đội Luân Hồi tân thủ: Mạnh Kỳ, Giang Chỉ Vi, Trương Viễn Sơn, Tề Chính Ngôn, Thích Hạ, Thanh Cảnh.
- Nhiệm vụ: Ẩn Hoàng Bảo (Thù lao: Thiện Công).
- Cố Tiểu Tang: Trùng sinh tại Tố Nữ Đạo mang ký ức kiếp trước, bắt đầu bố cục che chở Mạnh Kỳ.
"""
import os, sys, json
from fanfic_pipeline.core.state_manager import ProjectStateManager
from fanfic_pipeline.core.models import PointOfDivergence, CharacterVoice, RelationshipState
from fanfic_pipeline.core.model_router import PipelineModelRouter, AgentModelConfig
from fanfic_pipeline.core.engine import FanficEngine

def run_e2e_rebirth(num_chapters: int = 3):
    project_id = "fanfic_gu_xiaosang_rebirth"
    os.environ["CLIPROXY_KEY"] = "cpa-local-9f3a7e2b1c4d"
    
    mgr = ProjectStateManager(project_id)
    
    pod = PointOfDivergence(
        divergence_anchor="Chương 1-8: Trước thềm Nhiệm vụ Luân Hồi Tân Thủ (Ẩn Hoàng Bảo)",
        what_if_premise="Cố Tiểu Tang tự sát đoạn tuyệt Kim Mẫu, chân linh trùng sinh về thời điểm trước nhiệm vụ Ẩn Hoàng Bảo, bắt đầu từ Tố Nữ Đạo âm thầm can thiệp Lục Đạo để bảo hộ Mạnh Kỳ.",
        butterfly_effects=[
            "Cố Tiểu Tang không còn là kẻ thù mà âm thầm để lại manh mối/bí kíp cho Mạnh Kỳ",
            "Mạnh Kỳ sớm nhận ra sự bất thường của Lục Đạo và thân phận Tô Tử Viễn",
            "Đội ngũ tân thủ (Chỉ Vi, Viễn Sơn, Chính Ngôn, Thích Hạ) được cảnh báo sớm về cạm bẫy Ẩn Hoàng Bảo"
        ],
        frozen_canon=[
            "Bối cảnh mở đầu: Mạnh Kỳ là tạp dịch tăng Chân Định ở Thiếu Lâm Tự cùng Chân Tuệ",
            "Đội Luân Hồi tân thủ gồm 6 người: Mạnh Kỳ, Giang Chỉ Vi, Trương Viễn Sơn, Tề Chính Ngôn, Thích Hạ, Thanh Cảnh",
            "Nhiệm vụ Luân Hồi thứ nhất: Ẩn Hoàng Bảo (Thù lao: Thiện Công)",
            "Luật Lục Đạo Luân Hồi không đổi"
        ]
    )

    voices = {
        "meng_qi": CharacterVoice(
            character_id="meng_qi", name="Mạnh Kỳ", gender="Nam",
            personality_core="[Chân Định] Tiểu hòa thượng Thiếu Lâm, pháp danh Chân Định, sợ chết, lươn lẹo, thích trang bức, nhưng trọng tình nghĩa.",
            dialogue_rhythm="Dí dỏm, nội tâm hay吐槽 (cà khịa), gọi 'A Di Đà Phật' khi chột dạ.",
            moral_boundaries="Không hại người vô tội, không bỏ rơi đồng đội.", secret_motive="Tìm cơ hội hoàn tục làm đại hiệp."
        ),
        "gu_xiaosang": CharacterVoice(
            character_id="gu_xiaosang", name="Cố Tiểu Tang", gender="Nữ",
            personality_core="[Trùng Sinh Yêu Nữ] Thánh nữ Tố Nữ Đạo, mang ký ức kiếp trước chết dưới tay Kim Mẫu, thâm tình giấu kín sau nụ cười mị hoặc.",
            dialogue_rhythm="Nửa cười nửa đùa, gọi 'Tướng công', tâm tư sâu không lường được.",
            moral_boundaries="Tất cả vì bảo hộ Mạnh Kỳ và bản thân thoát khỏi kiếp Đạo Tiêu.", secret_motive="Trảm diệt Vô Sinh Lão Mẫu."
        ),
        "jiang_zhiwei": CharacterVoice(
            character_id="jiang_zhiwei", name="Giang Chỉ Vi", gender="Nữ",
            personality_core="[Kiếm Xuất Vô Hối] Đệ tử Tẩy Kiếm Các, kiếm tâm thuần túy, tính tình hào sảng, trọng lời hứa.",
            dialogue_rhythm="Dứt khoát, thanh thúy, thẳng thắn.",
            moral_boundaries="Chính đạo hiệp nghĩa, kiếm không chém kẻ yếu vô tội."
        ),
        "qi_zhengyan": CharacterVoice(
            character_id="qi_zhengyan", name="Tề Chính Ngôn", gender="Nam",
            personality_core="[Hoán Hoa Kiếm Phái] Mặt đơ ít nói, xuất thân bình dân, nội tâm kiên định.",
            dialogue_rhythm="Cộc lốc, vài chữ một câu.",
            moral_boundaries="Bình đẳng chúng sinh, bảo vệ đồng đội."
        )
    }

    relationships = [
        RelationshipState(
            pair=["gu_xiaosang", "meng_qi"],
            trope_type="Rebirth Protector",
            intimacy_level=9,
            current_dynamic="Tiểu Tang đơn phương bảo hộ từ trong bóng tối; Mạnh Kỳ chưa hề hay biết.",
            unspoken_conflicts=["Ký ức kiếp trước nếu để Lục Đạo hoặc Kim Mẫu biết sẽ dẫn tới hủy diệt"]
        )
    ]

    mgr.init_project("Nhất Thế Chi Tôn: Tiểu Tang Trùng Sinh", "Nhất Thế Chi Tôn", pod, voices, relationships)

    cfg = AgentModelConfig(
        provider="cliproxyapi",
        model_name="deepseek-v4-flash-free",
        base_url="http://47.237.140.200/v1",
        api_key_env="CLIPROXY_KEY",
        temperature=0.7,
        max_tokens=4096
    )
    router = PipelineModelRouter(
        architect_agent=cfg, composer_agent=cfg, writer_agent=cfg,
        ooc_critic_agent=cfg, canon_critic_agent=cfg,
        relationship_critic_agent=cfg, pacing_critic_agent=cfg
    )
    
    engine = FanficEngine(state_mgr=mgr, model_router=router)
    
    print(f"🚀 BẮT ĐẦU CHẠY PIPELINE CHUẨN NGUYÊN TÁC 100% (Dự án: {project_id})...")
    
    instructions = [
        "Chương 1: Mở đầu tại Thiếu Lâm Tự. Tạp dịch tăng Chân Định (Mạnh Kỳ) quét tuyết tại Thiền Tâm Viện cùng Chân Tuệ. Cùng lúc đó tại Tố Nữ Đạo, Cố Tiểu Tang thức tỉnh ký ức trùng sinh, mỉm cười nhìn về phương bắc chuẩn bị bảo hộ tướng công.",
        "Chương 2: Đêm kinh biến. Mạnh Kỳ mơ thấy phương trượng Thiếu Lâm chứng La Hán Kim Thân vỗ một chưởng, giật mình tỉnh dậy phát hiện mình rơi vào Quảng trường Luân Hồi. Hội ngộ 5 đồng đội tân thủ: Giang Chỉ Vi (Tẩy Kiếm Các), Trương Viễn Sơn (Chân Võ), Tề Chính Ngôn (Hoán Hoa), Thích Hạ, Thanh Cảnh.",
        "Chương 3: Bảng Luân Hồi & Nhiệm vụ Ẩn Hoàng Bảo. Cả đội xem xét bảng đổi công pháp (Thái Thượng Kiếm Kinh, Thiên Đế Ngọc Sách). Lục Đạo ban bố nhiệm vụ ám sát bảo chủ Ẩn Hoàng Bảo, thù lao Thiện Công. Nhưng Mạnh Kỳ phát hiện trong tay áo mình có một phong thư kỳ lạ do Tiểu Tang âm thầm truyền vào."
    ]

    for ch in range(1, num_chapters + 1):
        print(f"\n=======================================================")
        print(f"📝 ĐANG CHẤP BÚT CHƯƠNG {ch} CHUẨN CANON QUA DEEPSEEK-V4-FLASH...")
        print(f"=======================================================")
        
        outline, draft, critique, state_delta = engine.run_chapter_step(
            chapter_num=ch,
            author_instruction=instructions[ch - 1]
        )
        
        commit_res = engine.commit_chapter(
            chapter_num=ch,
            draft=draft,
            outline=outline,
            state_delta=state_delta
        )
        print(f"💾 ATOMIC COMMIT: {commit_res.get('status', 'OK')} | Bản thảo lưu tại: {commit_res.get('chapter_path', '')}")
        
        print(f"\n📖 [TRÍCH ĐOẠN CHƯƠNG {ch}: {draft.title}] ({draft.word_count} chữ):")
        print("-------------------------------------------------------")
        print(draft.content[:600].strip() + "...\n")

if __name__ == "__main__":
    ch_count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    run_e2e_rebirth(ch_count)
