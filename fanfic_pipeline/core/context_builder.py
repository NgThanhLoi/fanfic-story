
"""
ContextCompiler + SealedWriterPacket v1.1 (FR-26, FR-28, FR-29):
- Epistemic filtering: writer sees only POV-visible facts
- Critic gets independent broader retrieval
- Token budgeting CJK-aware, rule stack
"""
import hashlib, re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def _estimate_tokens(text: str) -> int:
    cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
    words = len(re.findall(r'\S+', text))
    # ~1 token per 1.35 CJK chars or 0.75 words
    return max(1, round(cjk/1.35 + words*0.75)) if text else 0

class SealedWriterPacket(BaseModel):
    packet_id: str
    packet_hash: str
    chapter_number: int
    pov_character: str
    task_section: str
    state_section: str
    arc_section: str
    character_lenses: str
    canon_evidence: str
    story_memory: str
    style_contract: str
    rules_section: str
    token_budget: Dict[str,int] = Field(default_factory=dict)
    retrieval_trace: List[Dict[str,Any]] = Field(default_factory=list)
    rule_stack: List[str] = Field(default_factory=list)
    sealed: bool = True
    # P2 — butterfly (optional, not breaking v1)
    canon_time_max: int = 0
    counterfactual: Dict[str, Any] = Field(default_factory=dict)
    ripples_due: List[Dict[str,Any]] = Field(default_factory=list)
    forbidden: List[str] = Field(default_factory=list)

class ContextPackage(BaseModel):
    task_section: str
    current_state_section: str
    arc_context_section: str
    character_voice_section: str
    canon_evidence_section: str
    story_memory_section: str
    world_rules_section: str
    retrieval_log: List[Dict[str, Any]] = Field(default_factory=list)

class ContextCompiler:
    def __init__(self, canon_store=None, memory_engine=None, planner=None, enrichment_store=None):
        self.canon_store = canon_store
        self.memory_engine = memory_engine
        self.planner = planner
        self.enrichment_store = enrichment_store

    def _filter_canon_by_epistemic(self, hits: List[Dict], forbidden: List[str]) -> List[Dict]:
        if not forbidden: return hits
        forb_low = [f.lower() for f in forbidden]
        filtered=[]
        for h in hits:
            txt_low = (h.get("title","")+h.get("text","")).lower()
            if any(f in txt_low for f in forb_low):
                continue
            filtered.append(h)
        return filtered

    def compile_writer_packet(self, chapter_num: int, pov_character: str, active_characters: List[str],
                               full_state: Dict[str,Any], planner_ctx: Dict[str,Any],
                               canon_hits: List[Dict], memory_hits: List[Dict],
                               voices: Dict[str,Any], author_instruction: str = "") -> SealedWriterPacket:
        forbidden = planner_ctx.get("forbidden_knowledge", [])
        visible_canon = self._filter_canon_by_epistemic(canon_hits, forbidden)
        # Build sections
        task = f"CHƯƠNG {chapter_num} (POV: {pov_character})\nChỉ đạo: {author_instruction}" if author_instruction else f"CHƯƠNG {chapter_num} (POV: {pov_character})"
        status_text = full_state.get('character_status', '')
        state_sec = f"Địa điểm: {full_state.get('current_location','')}\nNhân vật: {', '.join(active_characters)}\nTrạng thái sức khỏe: {status_text or 'Bình thường, sẵn sàng giao chiến'}\nThiện công: {full_state.get('team_thien_cong',{})}\nCảnh giới: {full_state.get('character_realms',{})}"

        arc_sec = f"Quyển: {planner_ctx.get('volume_title','')} | Phân đoạn: {planner_ctx.get('arc_title','')}\nMục tiêu: {planner_ctx.get('mini_arc_objective','')}\nPhục bút: {'; '.join(planner_ctx.get('due_hooks',[]))}"
        # Dynamic voice, timeline snapshot and epistemic boundary from CanonIntelligenceEngine
        try:
            from fanfic_pipeline.packages.canon.canon_intelligence import CanonIntelligenceEngine
            t_snap = CanonIntelligenceEngine.get_timeline_snapshot(chapter_num)
            arc_sec += f"\n[ĐẠI CHIẾN DỊCH CANON]: {t_snap['active_grand_arc']}\n- Kẻ giật dây ngầm: {t_snap['mastermind_shadow']}\n- Mưu đồ: {t_snap['underlying_conspiracy']}"
            ep_bound = CanonIntelligenceEngine.get_epistemic_boundary(pov_character, chapter_num)
            if ep_bound.get("forbidden"):
                if not forbidden: forbidden = []
                forbidden.extend(ep_bound["forbidden"])
        except Exception:
            pass

        voice_lines = []
        for c in active_characters:
            if c in voices:
                v = voices[c]
                # Stage-aware dynamic voice evolution
                try:
                    from fanfic_pipeline.packages.canon.canon_intelligence import CanonIntelligenceEngine
                    if hasattr(v, "personality_core"):
                        v = CanonIntelligenceEngine.get_voice_for_chapter(c, chapter_num, v)
                except Exception:
                    pass
                if hasattr(v, "dialogue_rhythm"):
                    voice_lines.append(f"- {v.name}: {v.personality_core} | Khẩu khí: {v.dialogue_rhythm}")
                else:
                    voice_lines.append(f"- {v.get('name',c)}: {v.get('dialogue_rhythm','')}")
            elif self.enrichment_store:
                ent = self.enrichment_store.query_entity(c)
                if ent:
                    voice_lines.append(f"- {ent.canonical_name}: (Xuất hiện từ ch.{ent.first_seen_chapter})")

        # Include relationship context & dynamic voice from style package
        if len(active_characters) >= 2:
            try:
                from fanfic_pipeline.packages.style.character_voice_arc import get_voice_dynamics
                vd = get_voice_dynamics(active_characters[0], active_characters[1])
                voice_lines.append(f"\n[KHẨU KHÍ QUAN HỆ ({vd.character} x {vd.intimacy_with})]:\n- Đối thoại: {vd.banter_tone}\n- Chiến đấu: {vd.combat_tone}")
            except Exception:
                pass

        if self.enrichment_store:
            rel_lines = []
            for c in active_characters:
                rels = self.enrichment_store.query_relationships(c)
                for r in rels[:2]:
                    other = r.to_entity if r.from_entity == c else r.from_entity
                    if other in active_characters:
                        rel_lines.append(f"  * Quan hệ {c} - {other}: {r.type}")
            if rel_lines:
                voice_lines.append("\n[QUAN HỆ NHÂN VẬT]:\n" + "\n".join(list(set(rel_lines))))

        character_lenses = "\n".join(voice_lines) if voice_lines else "Không có lens đặc biệt"

        if forbidden:
            character_lenses += f"\n[VÙNG CẤM TRI THỨC - CẤM ĐỂ LỘ]: {', '.join(forbidden)}"
        canon_sec = "\n".join([f"- [{h.get('type','canon')}] {h.get('title','')}: {h.get('text','')[:400]}" for h in visible_canon]) if visible_canon else "Không có trích đoạn đặc biệt."
        memory_sec = "\n".join([f"- [Ch.{m.get('chapter',0)}] {m.get('topic','')}: {m.get('content','')[:300]}" for m in memory_hits]) if memory_hits else "Chưa có hồi ức liên quan."
        
        # Dynamic style contract from style system
        try:
            from fanfic_pipeline.packages.style.scene_classifier import classify_scene
            from fanfic_pipeline.packages.style.tone_modifier import get_dynamic_style_contract
            scene_mode = classify_scene(author_instruction, planner_ctx.get('arc_title',''))
            style_sec = get_dynamic_style_contract(scene_mode, active_characters)
        except Exception:
            style_sec = "Giữ văn phong Nhất Thế Chi Tôn: đao ý lẫm liệt, kiếm tâm thông minh, đối thoại tự nhiên, SHOW-DON'T-TELL."

        rules_sec = "Quy tắc Lục Đạo: Tuyệt đối không tiết lộ thân phận Lục Đạo. Tu vi Khai Khiếu chưa thể ngự không."
        rule_stack = ["hard_fact: frozen canon", "author_intent: " + (author_instruction[:80] if author_instruction else "none"), "arc_planning: " + planner_ctx.get('arc_title',''), "current_task: ch"+str(chapter_num), "style: xianxia"]

        # token budget
        sections = {"task": task, "state": state_sec, "arc": arc_sec, "lenses": character_lenses, "canon": canon_sec, "memory": memory_sec, "style": style_sec, "rules": rules_sec}
        budget = {k: _estimate_tokens(v) for k,v in sections.items()}
        budget["total"] = sum(budget.values())
        # packet hash
        raw = "|".join([task, state_sec, arc_sec, canon_sec, memory_sec])
        phash = _sha16(raw)
        pid = f"pkt_ch{chapter_num:04d}_{phash[:8]}"
        packet = SealedWriterPacket(
            packet_id=pid, packet_hash=phash, chapter_number=chapter_num, pov_character=pov_character,
            task_section=task, state_section=state_sec, arc_section=arc_sec,
            character_lenses=character_lenses, canon_evidence=canon_sec, story_memory=memory_sec,
            style_contract=style_sec, rules_section=rules_sec, token_budget=budget,
            retrieval_trace=canon_hits + memory_hits, rule_stack=rule_stack, sealed=True
        )
        return packet


    def compile_writer_packet_v2(self, chapter_num: int, pov_character: str, active_characters: List[str],
                                  full_state: Dict[str,Any], planner_ctx: Dict[str,Any],
                                  canon_hits: List[Dict], memory_hits: List[Dict],
                                  voices: Dict[str,Any], author_instruction: str = "",
                                  canon_time_max: int = 0,
                                  counterfactual: Optional[Dict[str,Any]] = None,
                                  ripples_due: Optional[List[Dict]] = None,
                                  forbidden: Optional[List[str]] = None) -> SealedWriterPacket:
        base = self.compile_writer_packet(chapter_num, pov_character, active_characters, full_state, planner_ctx, canon_hits, memory_hits, voices, author_instruction)
        if counterfactual: base.counterfactual = counterfactual
        if canon_time_max: base.canon_time_max = canon_time_max
        if ripples_due: base.ripples_due = ripples_due
        if forbidden: base.forbidden = forbidden
        # Re-hash with butterfly fields
        import hashlib
        raw = "|".join([base.task_section, base.state_section, base.arc_section, base.canon_evidence, base.story_memory, str(canon_time_max), str(forbidden or [])])
        base.packet_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        base.packet_id = f"pkt_ch{chapter_num:04d}_{base.packet_hash[:8]}"
        # Append butterfly section to rules for writer visibility
        if forbidden:
            base.rules_section += "\n\n[BUTTERFLY — KHÔNG ĐƯỢC VIẾT NGƯỢC]: " + "; ".join(forbidden[:4])
        if ripples_due:
            base.arc_section += "\n[Ripples đến hạn]: " + "; ".join([r.get('expected_manifestation','')[:50] for r in ripples_due[:3]])
        return base

    def compile_critic_packet(self, chapter_num: int, draft_text: str, full_state: Dict[str,Any], canon_store=None, pod=None) -> Dict[str,Any]:
        # Independent broader retrieval (no epistemic filter)
        cs = canon_store or self.canon_store
        hits=[]
        if cs:
            hits = cs.search_canon(draft_text[:500], chapter_context=chapter_num, top_k=6)
        return {"chapter_number": chapter_num, "independent_canon_facts": hits, "full_state": full_state, "pod_premise": getattr(pod, 'what_if_premise', '') if pod else ""}

# Backward compat wrapper
class ContextBuilder(ContextCompiler):
    def build_writer_context(self, chapter_num, pov_character, active_characters, current_state, author_instruction, voices):
        # Legacy ContextPackage path
        h_ctx = {}
        if self.planner:
            try: h_ctx = self.planner.get_hierarchical_context(chapter_num, pov_character)
            except: h_ctx = {}
        canon_hits=[]
        if self.canon_store:
            try: canon_hits = self.canon_store.search_canon(author_instruction + " " + h_ctx.get('mini_arc_objective',''), chapter_context=chapter_num, top_k=3)
            except: pass
        memory_hits=[]
        if self.memory_engine:
            try: memory_hits = self.memory_engine.search(author_instruction, current_chapter=chapter_num, top_k=3)
            except: pass
        packet = self.compile_writer_packet(chapter_num, pov_character, active_characters, current_state, h_ctx, canon_hits, memory_hits, voices, author_instruction)
        # Return legacy shape
        return ContextPackage(
            task_section=packet.task_section, current_state_section=packet.state_section,
            arc_context_section=packet.arc_section, character_voice_section=packet.character_lenses,
            canon_evidence_section=packet.canon_evidence, story_memory_section=packet.story_memory,
            world_rules_section=packet.rules_section, retrieval_log=packet.retrieval_trace
        )
    def build_critic_context(self, chapter_num, draft_text, pod_premise):
        cs = self.canon_store
        hits=[]
        if cs:
            try: hits = cs.search_canon(draft_text[:500], chapter_context=chapter_num, top_k=4)
            except: pass
        return {"chapter_number": chapter_num, "pod_premise": pod_premise, "independent_canon_facts": hits}
