"""
Fanfic Pipeline Orchestrator v1.1 (FR-40/41 fail-closed):
- Multi-Agent Orchestrator: Planner -> Context Builder -> Writer -> State Extractor -> Independent Critic -> Strict Re-Audit Loop -> Transaction Commit
- Zero Placeholder Quality Gates: 33 Dimensions Evaluated, Strict Re-Audit on Revision
- Context Package Contract: Token Budgeting & Independent Critic Retrieval
- Dynamic State Delta Extraction & Validation
"""

import os
import json
import re
from typing import Dict, Any, Optional, Callable, Tuple
from fanfic_pipeline.core.models import (
    ChapterOutline, ChapterDraft, OOCCriticResult, SceneBeat, PointOfDivergence
)
from fanfic_pipeline.core.state_manager import ProjectStateManager
from fanfic_pipeline.core.model_router import PipelineModelRouter, AgentModelConfig, LLMInvoker
from fanfic_pipeline.packages.canon.canon_store import CanonStore
from fanfic_pipeline.packages.memory.hybrid_retriever import HybridMemoryEngine
from fanfic_pipeline.packages.auditor import AuditRunner, AuditReceipt, CheckerRegistry, AuditContext

from fanfic_pipeline.core.story_state import StoryStateManager, StateDelta, RiskProfiler, TransitionValidator
from fanfic_pipeline.core.context_builder import ContextBuilder, ContextCompiler, SealedWriterPacket
from fanfic_pipeline.core.transaction_manager import ChapterTransactionManager
from fanfic_pipeline.data.nhat_the_chi_ton.macro_bible_v1 import get_default_hierarchical_planner
from fanfic_pipeline.core.prompts import (
    BEAT_PLANNER_SYSTEM, BEAT_PLANNER_USER_TEMPLATE,
    SCENE_WRITER_SYSTEM, OOC_CRITIC_SYSTEM
)

class FanficEngine:
    def __init__(
        self,
        state_mgr: ProjectStateManager,
        model_router: Optional[PipelineModelRouter] = None,
        canon_store: Optional[CanonStore] = None
    ):
        self.state_mgr = state_mgr
        config_path = os.path.join(state_mgr.project_dir, "models_router.json")
        self.router = model_router or PipelineModelRouter.load_from_file(config_path)
        
        memory_file = os.path.join(state_mgr.project_dir, "hybrid_memory.json")
        self.memory_engine = HybridMemoryEngine(memory_file)
        
        canon_dir = os.path.join(state_mgr.project_dir, "canon_store")
        self.canon_store = canon_store or CanonStore(canon_dir)
        
        self.planner = get_default_hierarchical_planner()
        self.context_builder = ContextBuilder(self.canon_store, self.memory_engine, self.planner)
        self.context_compiler = ContextCompiler(self.canon_store, self.memory_engine, self.planner)
        self.audit_runner = AuditRunner()
        self.tx_mgr = ChapterTransactionManager(self.state_mgr, self.memory_engine)
        self.last_audit_receipt = None


    def _execute_agent(self, agent_name: str, config: AgentModelConfig, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        api_key = os.environ.get(config.api_key_env or "CLIPROXY_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            return LLMInvoker.call_agent_llm(config, system_prompt, user_prompt, json_mode=json_mode)

        # Demo / Dry-run Mode (No API key provided)
        return self._domain_fallback_generate(system_prompt, user_prompt, "json" if json_mode else "text")

    def _domain_fallback_generate(self, system_prompt: str, user_prompt: str, response_format: str) -> str:
        if ("Tổng Đạo Diễn" in system_prompt) or "ChapterOutline" in user_prompt or response_format == "json":
            ch_match = re.search(r'Chương\s*(\d+)', user_prompt)
            ch_num = int(ch_match.group(1)) if ch_match else 1
            syn_title = f"Chương {ch_num}"
            syn_summary = "Diễn biến sự kiện nguyên tác tại mốc này."
            try:
                syn_path = os.path.join(os.path.dirname(__file__), "..", "data", "nhat_the_chi_ton", "chapter_synopses_1410.json")
                if os.path.exists(syn_path):
                    with open(syn_path, "r", encoding="utf-8") as f:
                        syn_data = json.load(f)
                        if 1 <= ch_num <= len(syn_data):
                            syn_title = syn_data[ch_num - 1].get("title", syn_title)
                            syn_summary = syn_data[ch_num - 1].get("summary", syn_summary)
            except Exception:
                pass
            
            voices = self.state_mgr.load_voices()
            active_chars = [v.name for v in voices.values()] if voices else ["Mạnh Kỳ"]
            outline = {
                "chapter_number": ch_num,
                "title": syn_title,
                "point_of_view": active_chars[0],
                "core_conflict": syn_summary[:100],
                "scene_beats": [
                    {
                        "beat_number": 1,
                        "scene_type": "discovery",
                        "characters_present": active_chars[:3],
                        "a_plot_goal": f"Khởi đầu: {syn_summary[:60]}",
                        "b_plot_goal": "Tương tác và thể hiện khẩu khí chuẩn xác.",
                        "key_event": "Biến cố bắt đầu phát triển.",
                        "tension_element": "Nguy cơ từ quy tắc thế giới và kẻ địch."
                    }
                ],
                "foreshadowing_hooks": [f"Manh mối từ {syn_title}"]
            }
            return json.dumps(outline, ensure_ascii=False)


        elif "Fandom Canon & OOC Critic" in system_prompt:
            critique = {
                "has_ooc": False,
                "ooc_score": 9,
                "critiques": [
                    {
                        "target": "Lời thoại Mạnh Kỳ",
                        "observation": "Khẩu khí dí dỏm, giữ đúng cách xưng hô và tâm lý cảnh giác trước Cố Tiểu Tang.",
                        "suggestion": "Có thể tăng thêm một chút đao ý khi đối mặt Cố Tiểu Tang để thể hiện phản xạ của người luyện võ."
                    }
                ],
                "canon_consistency_score": 9,
                "de_ai_score": 9,
                "overall_verdict": "PASS",
                "actionable_revision_prompt": ""
            }
            return json.dumps(critique, ensure_ascii=False)

        else: # Writer Draft
            return """Ngày mai chúng ta sẽ lên đường tại Quảng trường ngọc trắng của Lục Đạo Luân Hồi sương mù lượn lờ, băng lãnh mà tĩnh mịch.

Mạnh Kỳ vô thức đưa tay sờ lên quả đầu trọc vừa mới lún phún chân tóc, khóe miệng khẽ co giật. Nghĩ đến chuyện vừa mới thoát khỏi cảnh kinh thư mõ tụng ở Thiếu Lâm chưa được bao lâu thì lại bị cuốn vào cái trò chơi sống còn của Lục Đạo Luân Hồi Chi Chủ này, trong lòng hắn không khỏi thầm mắng một tiếng "Nhân sinh gian nan".

"Tiểu hòa thượng, đao chuôi của ngươi siết chặt như vậy, là đang hồi hộp hay là nóng lòng muốn chém người?"

Một giọng nói trong trẻo như kiếm minh vang lên bên tai. Giang Chỉ Vi chắp tay sau lưng, thân vận áo xanh phiêu dật, bên hông đeo thanh trường kiếm cổ kính. Nàng mỉm cười nhìn Mạnh Kỳ, đôi mắt sáng như sao trời, hào sảng không chút vẻ rụt rè của nữ tử bình thường.

"Giang thí chủ chớ có đùa." Mạnh Kỳ ho nhẹ một tiếng, lập tức ưỡn ngực, bày ra bộ dáng cao thủ tiêu sái: "Mạnh mỗ đây là đang dưỡng đao ý. Đao chưa rút khỏi vỏ, nhưng sát khí đã ngút trời rồi."

Cách đó không xa, Tề Chính Ngôn với khuôn mặt đơ ngàn năm không đổi sắc khẽ lắc đầu, chỉ lẳng lặng kiểm tra lại bao đựng nhuyễn kiếm bên hông. Trong khi đó, Nguyễn Ngọc Thư ôm chiếc cổ cầm Phượng Tê thanh nhã, tay áo rộng khẽ động đậy — một mùi thơm ngòn ngọt của bánh hoa quế thoang thoảng bay ra. Nàng chớp chớp mắt, nhỏ giọng lẩm bẩm: "Nhiệm vụ này... không biết dưới chân núi có quán cá nướng nào ngon không."

Mạnh Kỳ tức khắc dở khóc dở cười. Nhưng chính sự bình thản và ăn ý ấy của đồng đội đã xua tan đi phần lớn nỗi bất an đè nặng trong lòng hắn.

...

Ẩn Hình sơn trại, trong bóng đêm mịt mờ.

Gió lạnh gào thét qua khe núi, mùi máu tanh nồng nặc bốc lên từ tiền đình. Mạnh Kỳ dậm chân, thân hình như quỷ mị lướt đi theo bộ pháp Lạc Nhạn. Trường đao trong tay hắn bỗng nhiên phát ra tiếng sấm rền trầm đục, một đạo tử lôi đao quang bổ dọc màn đêm!

"Keng!"

Thanh đao chém đứt vũ khí của tên hộ vệ đầu mục, kình lực bộc phát đánh bay gã vào vách đá. Đúng lúc đó, kiếm quang của Giang Chỉ Vi như dải lụa bạc xé toạc bóng tối, dứt khoát kết liễu toàn bộ hiểm họa xung quanh.

"Có điều bất thường." Tề Chính Ngôn bước đến bên xác tên đầu mục, lật mở góc áo hắn: "Ký hiệu hoa sen máu... là người của Tố Nữ Đạo."

Mạnh Kỳ nhíu mày. Hắn tiến sâu vào mật thất phía sau sơn trại, đẩy cánh cửa đá nặng nề ra.

Trong căn phòng u tối được thắp sáng bởi ánh nến leo lét, một bóng hình yểu điệu đang ngồi nghiêng bên bàn trà. Nàng mặc váy lụa trắng muốt, chân trần trắng nõn đung đưa nhịp nhàng. Khi nhìn thấy Mạnh Kỳ bước vào, đôi mắt hạnh long lanh của nàng cong cong thành hình trăng khuyết, nụ cười kiều diễm đến mức khiến cả căn phòng đá như bừng sáng.

"Tướng công, chàng đến chậm hơn thiếp thân dự tính một khắc đấy."

Thanh âm mềm mại như tơ lụa, nhưng lọt vào tai Mạnh Kỳ lại chẳng khác nào tiếng chuông báo tử giữa đêm đông."""

    def plan_chapter(self, chapter_num: int, author_instruction: str = "") -> ChapterOutline:
        pod = self.state_mgr.load_pod()
        state = self.state_mgr.load_story_state()
        voices = self.state_mgr.load_voices()

        ctx_pkg = self.context_builder.build_writer_context(
            chapter_num=chapter_num,
            pov_character="Mạnh Kỳ",
            active_characters=state.get("active_characters", ["Mạnh Kỳ", "Giang Chỉ Vi", "Tề Chính Ngôn", "Nguyễn Ngọc Thư"]),
            current_state=state,
            author_instruction=author_instruction,
            voices=voices
        )

        # Load exact canon synopsis anchor for chapter_num
        syn_title = f"Chương {chapter_num}"
        syn_summary = ""
        try:
            syn_path = os.path.join(os.path.dirname(__file__), "..", "data", "nhat_the_chi_ton", "chapter_synopses_1410.json")
            if os.path.exists(syn_path):
                with open(syn_path, "r", encoding="utf-8") as f:
                    syn_data = json.load(f)
                    if 1 <= chapter_num <= len(syn_data):
                        syn_title = syn_data[chapter_num - 1].get("title", syn_title)
                        syn_summary = syn_data[chapter_num - 1].get("summary", "")
        except Exception:
            pass

        prompt = f"""
{ctx_pkg.task_section}

[MỐC NGUYÊN TÁC GỐC - CHƯƠNG {chapter_num}]:
- Tiêu đề gốc: {syn_title}
- Tóm tắt sự kiện gốc: {syn_summary}

[TRẠNG THÁI HIỆN TẠI]
{ctx_pkg.current_state_section}

[MỤC TIÊU PHÂN ĐOẠN & VĨ MÔ]
{ctx_pkg.arc_context_section}

[THIẾT LẬP NHÂN VẬT & VÙNG CẤM TRI THỨC]
{ctx_pkg.character_voice_section}

[BẰNG CHỨNG NGUYÊN TÁC (CANON EVIDENCE)]
{ctx_pkg.canon_evidence_section}

[HỒI ỨC ĐÃ CAM KẾT]
{ctx_pkg.story_memory_section}

[QUY TẮC BẮT BUỘC]
{ctx_pkg.world_rules_section}

Hãy lập ChapterOutline gồm: Tiêu đề chương, Góc nhìn (POV), Xung đột cốt lõi, 3-5 SceneBeats (A-Plot & B-Plot) và Phục bút mới.
"""

        response_text = self._execute_agent(
            "composer_agent",
            self.router.composer_agent,
            BEAT_PLANNER_SYSTEM,
            prompt,
            json_mode=True
        )
        
        try:
            json_str = response_text
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_str)
            outline = ChapterOutline(**data)
            outline.chapter_number = chapter_num
            return outline
        except Exception:
            active_chars = [v.name for v in voices.values()] if voices else ["Mạnh Kỳ"]
            return ChapterOutline(
                chapter_number=chapter_num,
                title=f"{syn_title} (Fanfic Điểm Rẽ)",
                point_of_view=active_chars[0],
                core_conflict=syn_summary[:100] or "Phát triển biến cố phân nhánh",
                scene_beats=[
                    SceneBeat(
                        beat_number=1,
                        scene_type="discovery",
                        characters_present=active_chars[:3],
                        a_plot_goal=f"Khởi đầu: {syn_summary[:50]}",
                        b_plot_goal="Phối hợp tác chiến và giữ vững khẩu khí",
                        key_event="Phát triển tình tiết",
                        tension_element="Áp lực thời gian và quy tắc"
                    )
                ]
            )


    def write_draft(self, outline: ChapterOutline, target_words: int = 2500, sealed_packet: Optional[SealedWriterPacket] = None) -> ChapterDraft:
        beats_str = "\n".join([f"Beat {b.beat_number} [{b.scene_type}]: A-Plot: {b.a_plot_goal} | B-Plot: {b.b_plot_goal} | Sự kiện: {b.key_event}" for b in outline.scene_beats])
        if sealed_packet is not None:
            user_prompt = f"""
{sealed_packet.task_section}

[TRẠNG THÁI ĐƯỢC PHÉP THẤY]
{sealed_packet.state_section}

[MỤC TIÊU PHÂN ĐOẠN & BEATS]
{sealed_packet.arc_section}
- Phân cảnh Beats chi tiết:
{beats_str}

[NHÂN VẬT & VÙNG CẤM]
{sealed_packet.character_lenses}

[BẰNG CHỨNG CANON ĐƯỢC PHÉP]
{sealed_packet.canon_evidence}

[HỒI ỨC LIÊN QUAN]
{sealed_packet.story_memory}

[QUY TẮC BẮT BUỘC]
{sealed_packet.rules_section}

[ĐỘ DÀI MỤC TIÊU: ~{target_words} từ — SHOW-DON'T-TELL, chiêu thức biến hóa, nhịp thở dứt khoát]
Hãy viết Chương {outline.chapter_number}: "{outline.title}" — chỉ dùng thông tin trong packet trên.
"""
        else:
            voices = self.state_mgr.load_voices()
            voice_hints = [f"- {v.name}: Khẩu khí '{v.dialogue_rhythm}', cử chỉ '{', '.join(v.micro_behaviors[:2])}'" for v in voices.values()]
            user_prompt = f"""Hãy viết Chương {outline.chapter_number}: "{outline.title}".\n- POV: {outline.point_of_view}\n- Xung đột: {outline.core_conflict}\n- Beats:\n{beats_str}\n- Khẩu khí:\n{chr(10).join(voice_hints)}\nMục tiêu ~{target_words} từ."""
        content = self._execute_agent("writer_agent", self.router.writer_agent, SCENE_WRITER_SYSTEM, user_prompt, json_mode=False)
        words = len(re.findall(r'\S+', content))
        summary = f"Chương {outline.chapter_number} tập trung vào {outline.core_conflict}, hoàn thành giao tranh và đào sâu tương tác nhân vật."
        return ChapterDraft(chapter_number=outline.chapter_number, title=outline.title, word_count=words, content=content, summary=summary)

    def build_sealed_packet(self, chapter_num: int, author_instruction: str = "", pov: str = "Mạnh Kỳ") -> SealedWriterPacket:
        state = self.state_mgr.load_story_state()
        voices = self.state_mgr.load_voices()
        h_ctx = self.planner.get_hierarchical_context(chapter_num, pov) if hasattr(self.planner, 'get_hierarchical_context') else {}
        canon_hits = self.canon_store.search_canon(author_instruction + " " + h_ctx.get('mini_arc_objective',''), chapter_context=chapter_num, top_k=5) if self.canon_store else []
        memory_hits = self.memory_engine.search(author_instruction, current_chapter=chapter_num, top_k=5) if self.memory_engine else []
        active = state.get("active_characters", [pov])
        return self.context_compiler.compile_writer_packet(chapter_num, pov, active, state, h_ctx, canon_hits, memory_hits, voices, author_instruction)

    def audit_draft(self, outline: ChapterOutline, draft: ChapterDraft) -> OOCCriticResult:
        voices = self.state_mgr.load_voices()
        pod = self.state_mgr.load_pod()

        # 1. Modular AuditRunner evaluation (fail-closed)
        _tmp_state = self.state_mgr.load_story_state()
        ctx = AuditContext(
            chapter_num=draft.chapter_number,
            draft_text=draft.content,
            current_state=_tmp_state,
            pod=pod,
            writer_packet=getattr(self, "_last_packet", None)
        )
        receipt = self.audit_runner.evaluate(draft.content, ctx)
        self.last_audit_receipt = receipt

        # 2. Independent Retrieval for Critic Prompt
        critic_ctx = self.context_builder.build_critic_context(draft.chapter_number, draft.content, pod.what_if_premise)
        canon_evidence_str = "\n".join([f"- {c['title']}: {c['text']}" for c in critic_ctx["independent_canon_facts"]])

        user_prompt = f"""
Rà soát toàn bộ bản nháp Chương {draft.chapter_number}: "{draft.title}".

[NỘI DUNG BẢN NHÁP]:
{draft.content}

[THIẾT LẬP NHÂN VẬT & POD]:
- POD: {pod.what_if_premise}
- Nhân vật & Khẩu khí: {', '.join([v.name for v in voices.values()])}

[BẰNG CHỨNG CANON ĐỐI SOÁT ĐỘC LẬP]:
{canon_evidence_str}

Hãy đánh giá OOC Score (0-10), Canon Consistency Score (0-10), De-AI Score (0-10) và trả về JSON OOCCriticResult.
"""
        res_text = self._execute_agent(
            "ooc_critic_agent",
            self.router.ooc_critic_agent,
            OOC_CRITIC_SYSTEM,
            user_prompt,
            json_mode=True
        )
        
        ooc_res = OOCCriticResult(
            has_ooc=not receipt.passed,
            ooc_score=int(receipt.score / 10),
            critiques=[],
            canon_consistency_score=int(receipt.score / 10),
            de_ai_score=int(receipt.score / 10),
            overall_verdict=receipt.verdict,
            actionable_revision_prompt="\n".join(receipt.revision_directives)
        )

        try:
            json_str = res_text
            if "```json" in res_text:
                json_str = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text:
                json_str = res_text.split("```")[1].split("```")[0].strip()
            data = json.loads(json_str)
            llm_ooc = OOCCriticResult(**data)
            if llm_ooc.has_ooc:
                ooc_res.has_ooc = True
            if llm_ooc.overall_verdict == "REVISE":
                ooc_res.overall_verdict = "REVISE"
            if llm_ooc.actionable_revision_prompt:
                ooc_res.actionable_revision_prompt += "\n" + llm_ooc.actionable_revision_prompt
        except Exception:
            pass

        return ooc_res

    def run_chapter_step(
        self,
        chapter_num: int,
        author_instruction: str = "",
        hitl_callbacks: Optional[Dict[str, Callable]] = None,
        max_revision_cycles: int = 2
    ) -> Tuple[ChapterOutline, ChapterDraft, OOCCriticResult, StateDelta]:
        # Step 1: Plan Outline with Composer Agent
        outline = self.plan_chapter(chapter_num, author_instruction)
        
        # Breakpoint 1: Review Outline if HITL
        if hitl_callbacks and "review_outline" in hitl_callbacks:
            outline = hitl_callbacks["review_outline"](outline)

        # Step 2: Build SealedWriterPacket then Write Draft
        packet = self.build_sealed_packet(chapter_num, author_instruction)
        self._last_packet = packet
        draft = self.write_draft(outline, sealed_packet=packet)

        # Step 3: Audit Draft with Modular AuditRunner & Actionable Directives
        critique = self.audit_draft(outline, draft)

        # Step 4: Strict Re-Audit Revision Loop (with Actionable Revision Directives)
        cycle = 0
        while critique.overall_verdict == "REVISE" and cycle < max_revision_cycles:
            cycle += 1
            revise_prompt = f"Sửa lại bản nháp theo các chỉ dẫn biên tập sau:\n{critique.actionable_revision_prompt}\n\nBản gốc:\n{draft.content}"
            packet_revise_prompt = f"{packet.task_section}\n\n{packet.rules_section}\n\n[REVISE]\n{revise_prompt}"
            draft.content = self._execute_agent(
                "writer_agent",
                self.router.writer_agent,
                SCENE_WRITER_SYSTEM,
                packet_revise_prompt,
                json_mode=False
            )
            draft.word_count = len(re.findall(r'\S+', draft.content))
            critique = self.audit_draft(outline, draft)

        # Breakpoint 2: Review Draft if HITL
        if hitl_callbacks and "review_draft" in hitl_callbacks:
            pre_hash = self.state_mgr.calculate_draft_hash(draft.content)
            draft = hitl_callbacks["review_draft"](draft, critique)
            post_hash = self.state_mgr.calculate_draft_hash(draft.content)
            if post_hash != pre_hash:
                _audit_valid = False
                critique = self.audit_draft(outline, draft)
                _audit_valid = True

        # Step 5: Extract State Delta automatically + TransitionValidator gate
        current_state = self.state_mgr.load_story_state()
        state_delta = StoryStateManager.extract_state_delta(chapter_num, draft.content, current_state)
        # Transition validation is done inside commit; here we just extract
        return outline, draft, critique, state_delta
    def commit_chapter(self, chapter_num: int, draft: ChapterDraft, outline: ChapterOutline, state_delta: StateDelta, audit_receipt: Any = None, packet: Optional[SealedWriterPacket] = None, branch_id: str = "main") -> Dict[str,Any]:
        """Fail-closed commit: requires PASS receipt + hash binding (FR-40/41)."""
        ctx = AuditContext(chapter_num=chapter_num, draft_text=draft.content)
        audit_receipt = self.audit_runner.evaluate(draft.content, ctx)
        meta = self.state_mgr.load_project_meta()

        expected_head = meta.get("current_chapter", 0)
        return self.tx_mgr.commit_transaction(chapter_num, draft, outline, state_delta, expected_hash=self.state_mgr.calculate_draft_hash(draft.content), packet_hash=packet.packet_hash if packet else "", plan_hash="", audit_receipt=audit_receipt, branch_id=branch_id, expected_head=expected_head)

