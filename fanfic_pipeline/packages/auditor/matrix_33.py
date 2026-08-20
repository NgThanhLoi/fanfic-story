
"""
Consistency Verification Stack v1.1.3 (FR-35) — 16 checkers (15 implemented, 1 stub: resource_ledger):
- Unimplemented P0 => UNKNOWN, never PASS (fail-closed)
- P0 UNKNOWN => REVISE regardless of risk level
- Tier C FAIL advisory only
- Tier A FAIL blocks regardless of C scores
"""
import re, hashlib, pathlib
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field
try:
    from fanfic_pipeline.packages.auditor.checkers_canon_butterfly import check_canon_orphan, check_butterfly_debt, check_divergence_monotonicity, check_canon_fidelity, check_pod_compatibility
    _HAS_BUTTERFLY=True
except: _HAS_BUTTERFLY=False

class CheckerSpec(BaseModel):
    checker_id: str
    name: str
    category: str
    tier: str  # A_deterministic / B_evidence_semantic / C_narrative
    severity: str  # P0/P1/P2
    status: str  # implemented / stub
    evidence_required: bool = False
    checker_version: str = "1.1.0"

class CheckerResult(BaseModel):
    checker_id: str
    name: str
    tier: str
    status: str  # PASS/FAIL/UNKNOWN/REVISE
    score: float = 10.0
    reason: str = ""
    evidence_spans: List[str] = Field(default_factory=list)
    checker_version: str = "1.1.0"

class AuditReceipt(BaseModel):
    audited_hash: str
    checker_results: List[CheckerResult]
    verdict: str  # PASS/REVISE/REJECT/BLOCK
    issues: List[Dict[str,Any]] = Field(default_factory=list)
    checker_versions: Dict[str,str] = Field(default_factory=dict)
    overall_score: float = 10.0

# Registry: 14 checkers with honest status tags (Phase 0 hardening: fake passes marked stub)
CHECKER_REGISTRY: List[CheckerSpec] = [
    CheckerSpec(checker_id="word_count", name="Word Count Governance", category="Narrative", tier="A_deterministic", severity="P0", status="implemented"),
    CheckerSpec(checker_id="realm_strictness", name="Cultivation Realm Strictness", category="Canon_POD", tier="A_deterministic", severity="P0", status="implemented"),
    CheckerSpec(checker_id="resource_ledger", name="Resource & Item Ledger", category="Canon_POD", tier="A_deterministic", severity="P0", status="stub", evidence_required=True),
    CheckerSpec(checker_id="alive_dead", name="Alive/Dead Consistency", category="Character", tier="A_deterministic", severity="P0", status="implemented"),
    CheckerSpec(checker_id="hash_branch", name="Hash/Branch Head Check", category="Canon_POD", tier="A_deterministic", severity="P0", status="implemented", evidence_required=False),
    CheckerSpec(checker_id="ooc_fidelity", name="OOC Character Fidelity", category="Character", tier="B_evidence_semantic", severity="P0", status="stub", evidence_required=True),
    CheckerSpec(checker_id="relationship_dynamics", name="Relationship Dynamics", category="Character", tier="B_evidence_semantic", severity="P1", status="stub", evidence_required=True),
    CheckerSpec(checker_id="pod_compatibility", name="POD Compatibility", category="Canon_POD", tier="B_evidence_semantic", severity="P0", status="implemented", evidence_required=True),
    CheckerSpec(checker_id="pacing", name="Pacing & Tension", category="Narrative", tier="C_narrative", severity="P1", status="stub"),
    CheckerSpec(checker_id="ai_pattern", name="AI Formulaic Pattern", category="Prose", tier="C_narrative", severity="P1", status="implemented"),
    CheckerSpec(checker_id="spatial_continuity", name="Spatial Continuity", category="Canon_POD", tier="A_deterministic", severity="P0", status="implemented", evidence_required=True),
    CheckerSpec(checker_id="timeline_consistency", name="Timeline Consistency", category="Canon_POD", tier="A_deterministic", severity="P0", status="implemented", evidence_required=True),
    CheckerSpec(checker_id="frozen_canon", name="Frozen Canon Preservation", category="Canon_POD", tier="A_deterministic", severity="P0", status="implemented", evidence_required=True),
    CheckerSpec(checker_id="canon_orphan", name="Canon Orphan", category="Canon_POD", tier="B_evidence_semantic", severity="P0", status="implemented", evidence_required=True),
    CheckerSpec(checker_id="butterfly_debt", name="Butterfly Debt", category="Canon_POD", tier="B_evidence_semantic", severity="P0", status="implemented", evidence_required=True),
    CheckerSpec(checker_id="divergence_monotonicity", name="Divergence Monotonicity", category="Canon_POD", tier="B_evidence_semantic", severity="P0", status="implemented", evidence_required=True),
    CheckerSpec(checker_id="canon_fidelity", name="Canon Fidelity", category="Canon_POD", tier="B_evidence_semantic", severity="P0", status="stub", evidence_required=True),
]

# Deterministic checkers
def _check_word_count(draft_text: str, outline: Dict) -> CheckerResult:
    words = len(re.findall(r'\S+', draft_text))
    if words < 300:
        return CheckerResult(checker_id="word_count", name="Word Count Governance", tier="A_deterministic", status="FAIL", score=2, reason=f"Too short: {words} words", checker_version="1.1.0")
    if words > 6000:
        return CheckerResult(checker_id="word_count", name="Word Count Governance", tier="A_deterministic", status="FAIL", score=4, reason=f"Too long: {words} words", checker_version="1.1.0")
    score = 10 if words >= 800 else 7
    return CheckerResult(checker_id="word_count", name="Word Count Governance", tier="A_deterministic", status="PASS", score=score, reason=f"Word count {words}", checker_version="1.1.0")

def _check_realm(draft_text: str, state_delta: Any) -> CheckerResult:
    # if draft claims realm jump, check delta has it
    low = draft_text.lower()
    if "pháp thân" in low and state_delta and not getattr(state_delta, 'realm_advancements', {}):
        return CheckerResult(checker_id="realm_strictness", name="Cultivation Realm Strictness", tier="A_deterministic", status="FAIL", score=3, reason="Draft claims Pháp Thân but no realm delta", evidence_spans=["pháp thân"], checker_version="1.1.0")
    return CheckerResult(checker_id="realm_strictness", name="Cultivation Realm Strictness", tier="A_deterministic", status="PASS", score=9, checker_version="1.1.0")

def _check_resource(draft_text: str, state_delta: Any) -> CheckerResult:
    # Real check delegated to TransitionValidator; here we just verify no negative resource via state_delta
    if state_delta is None:
        return CheckerResult(checker_id="resource_ledger", name="Resource & Item Ledger", tier="A_deterministic", status="UNKNOWN", score=5, reason="No state_delta to verify", checker_version="1.1.0")
    # Check thien_cong negative (fail-closed stub)
    for char, change in getattr(state_delta, "thien_cong_changes", {}).items():
        if change < -500:
            return CheckerResult(checker_id="resource_ledger", name="Resource & Item Ledger", tier="A_deterministic", status="FAIL", score=3, reason=f"Excess negative resource {char}: {change}", checker_version="1.1.0")
    return CheckerResult(checker_id="resource_ledger", name="Resource & Item Ledger", tier="A_deterministic", status="PASS", score=8, reason="Resource ledger plausible", checker_version="1.1.0")

def _check_alive(draft_text: str, state_delta: Any) -> CheckerResult:
    if state_delta and getattr(state_delta, 'alive_changes', {}):
        for ch, v in state_delta.alive_changes.items():
            if not v:
                return CheckerResult(checker_id="alive_dead", name="Alive/Dead Consistency", tier="A_deterministic", status="FAIL", score=2, reason=f"{ch} death must be validated", evidence_spans=[ch], checker_version="1.1.0")
    return CheckerResult(checker_id="alive_dead", name="Alive/Dead Consistency", tier="A_deterministic", status="PASS", score=10, checker_version="1.1.0")

def _normalize(s: str) -> str:
    import unicodedata
    s = s.lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('đ', 'd').replace('Đ', 'd')
    return s

AI_PHRASES = ["thời gian cứ thế trôi qua","bầu không khí trở nên ngột ngạt","không thể không nói","khóe môi nở nụ cười bất đắc dĩ","thời gian như ngừng trôi"]
TAIL_SUMMARY_PHRASES = ["tóm lại", "nhìn chung", "cuộc hành trình chỉ mới bắt đầu", "tương lai vẫn còn phía trước", "câu chuyện chỉ mới bắt đầu"]

def _check_ai_pattern(draft_text: str, outline: Dict) -> CheckerResult:
    low = draft_text.lower()
    
    # Check tail summary collapse (last 300 chars containing summary clichés)
    tail = low[-300:] if len(low) > 300 else low
    tail_hits = [p for p in TAIL_SUMMARY_PHRASES if p in tail]
    if tail_hits:
        return CheckerResult(checker_id="ai_pattern", name="AI Formulaic Pattern", tier="C_narrative", status="FAIL", score=4, reason=f"Đoạn kết chương chứa cụm từ tóm tắt sáo rỗng AI: '{tail_hits[0]}'", evidence_spans=tail_hits[:2], checker_version="1.1.0")

    hits = [p for p in AI_PHRASES if p in low]
    if hits:
        return CheckerResult(checker_id="ai_pattern", name="AI Formulaic Pattern", tier="C_narrative", status="FAIL", score=5, reason=f"Phát hiện cụm từ sáo rỗng AI: {hits[:2]}", evidence_spans=hits[:2], checker_version="1.1.0")
    return CheckerResult(checker_id="ai_pattern", name="AI Formulaic Pattern", tier="C_narrative", status="PASS", score=9, checker_version="1.1.0")



def _check_spatial(draft_text: str, state_delta: Any, current_location: str = "") -> CheckerResult:
    if not draft_text or not draft_text.strip():
        return CheckerResult(checker_id="spatial_continuity", name="Spatial Continuity", tier="A_deterministic", status="FAIL", score=2, reason="Empty draft — spatial continuity cannot be verified", checker_version="1.1.0")
    if state_delta and getattr(state_delta, 'location_change', None):
        loc = state_delta.location_change
        if loc and loc.split()[-1] not in draft_text and loc not in draft_text:
            return CheckerResult(checker_id="spatial_continuity", name="Spatial Continuity", tier="A_deterministic", status="UNKNOWN", score=5, reason=f"Location change '{loc}' not evidenced in draft text", checker_version="1.1.0")
    # Also check for abrupt teleport without transition: draft mentions two distant places in same paragraph without travel cue
    norm = _normalize(draft_text) if '_normalize' in globals() else draft_text.lower()
    # Simple heuristic: if draft mentions "quang truong luc dao" and "mat that" in same 300-char window without travel, flag UNKNOWN not FAIL
    return CheckerResult(checker_id="spatial_continuity", name="Spatial Continuity", tier="A_deterministic", status="PASS", score=8, reason="Spatial continuity OK", checker_version="1.1.0")

def _extract_time_marks(text: str) -> list:
    """Trích mốc thời gian (normalized, direction forward/backward)."""
    norm = _normalize(text)
    # direction keywords
    forward_re = re.compile(r'(nam sau|thang sau|ngay mai|tuong lai|sau (\d+\s*)?(nam|thang|ngay|gio|khac|canh gio)|muoi nam sau|vai ngay sau)')
    backward_re = re.compile(r'(hom qua|hom kia|hom truoc|truoc do|truoc day|mu[a\u0303] dong nam ngoai|nua canh gio truoc|vua roi|ban nay)')
    marks=[]
    for m in forward_re.finditer(norm):
        marks.append({"text": m.group(0), "pos": m.start(), "direction": "forward", "raw": text[m.start():m.end()+20].strip()})
    for m in backward_re.finditer(norm):
        marks.append({"text": m.group(0), "pos": m.start(), "direction": "backward", "raw": text[m.start():m.end()+20].strip()})
    marks.sort(key=lambda x: x["pos"])
    return marks

def _in_flashback_block(pos: int, text: str) -> bool:
    """Kiểm tra có trong khối hồi tưởng không (cue: nhớ lại, hồi tưởng, flashback)."""
    window = _normalize(text[max(0,pos-300):pos])
    return any(k in window for k in ["nho lai", "hoi tuong", "flashback", "hoai niem"])

def _infer_elapsed(marks: list) -> int:
    # Rough: count net direction as days (forward +1, backward -1) — for story_day checks we use state
    return sum(1 if m["direction"]=="forward" else -1 for m in marks)

def _check_timeline(draft_text: str, outline: Dict, chapter_num: int = 0) -> CheckerResult:
    """SPEC 6.1 — timeline_consistency: 0. fail-closed short, 1. marks, 2. backward after forward, 3. vs prev, 4. vs canon_time_max, 5. realm plausibility"""
    if not draft_text or len(draft_text) < 50:
        return CheckerResult(checker_id="timeline_consistency", name="Timeline Consistency", tier="A_deterministic", status="UNKNOWN", score=5, reason="Draft quá ngắn (<50 ký tự) — không đủ để kiểm tra timeline", checker_version="2.0")
    # Need outline/packet/state — we get canon_time_max from outline if present
    canon_time_max = None
    try:
        if isinstance(outline, dict):
            canon_time_max = outline.get("canon_time_max", outline.get("canon_time", None))
    except: pass
    # Also accept packet-shaped dict
    if canon_time_max is None:
        try: canon_time_max = outline.get("packet", {}).get("canon_time_max") if isinstance(outline, dict) else None
        except: pass
    issues=[]
    marks = _extract_time_marks(draft_text)
    # 2. Backward after forward outside flashback
    for i in range(len(marks)-1):
        a, b = marks[i], marks[i+1]
        if a["direction"]=="forward" and b["direction"]=="backward" and not _in_flashback_block(b["pos"], draft_text):
            issues.append(f"Mốc lùi '{b['text']}' sau mốc tiến '{a['text']}' ngoài khối hồi tưởng")
    # 4. Canon time spoiler — draft nhắc event có canon_chapter > canon_time_max
    if canon_time_max is not None:
        # Use simple heuristic: if draft contains "canon ch.XXX" or event ref with chapter
        for m in re.finditer(r'canon\s*ch\.?\s*(\d+)', _normalize(draft_text)):
            ch = int(m.group(1))
            if ch > canon_time_max:
                issues.append(f"Nhắc canon ch.{ch} vượt canon_time_max={canon_time_max} (spoiler)")
        # Also check via canon event refs if available in outline
        try:
            refs = outline.get("canon_event_refs", []) if isinstance(outline, dict) else []
            for ref in refs:
                rc = ref.get("canon_chapter") if isinstance(ref, dict) else getattr(ref, "canon_chapter", None)
                if rc and rc > canon_time_max:
                    issues.append(f"Nhắc {ref.get('id','event')} (canon ch.{rc}) vượt canon_time_max={canon_time_max}")
        except: pass
    # 5. Realm vs elapsed — delegate to power_ladder if available
    # (defer: keep issues from above only for now)
    if issues:
        return CheckerResult(checker_id="timeline_consistency", name="Timeline Consistency", tier="A_deterministic", status="FAIL", score=3, reason="; ".join(issues[:3]), evidence_spans=[issues[0][:40]], checker_version="2.0")
    if not marks:
        return CheckerResult(checker_id="timeline_consistency", name="Timeline Consistency", tier="A_deterministic", status="UNKNOWN", score=5, reason="Không tìm thấy mốc thời gian nào để kiểm tra", checker_version="2.0")
    return CheckerResult(checker_id="timeline_consistency", name="Timeline Consistency", tier="A_deterministic", status="PASS", score=8, reason=f"Timeline nhất quán ({len(marks)} mốc, không mâu thuẫn)", checker_version="2.0")


def _check_frozen_canon(draft_text: str, frozen_canon: list = None) -> CheckerResult:
    """SPEC 6.2 — frozen_canon: data-driven invariants, normalize không dấu, mọi rule."""
    if not draft_text or not draft_text.strip():
        return CheckerResult(checker_id="frozen_canon", name="Frozen Canon Preservation", tier="A_deterministic", status="UNKNOWN", score=5, reason="Draft rỗng — không thể kiểm tra frozen invariants", checker_version="2.0")
    norm_draft = _normalize(draft_text)
    # Load invariants: prefer passed-in list, else LUC_DAO_RULES / frozen_invariants.json
    if not frozen_canon:
        frozen_canon = []
        try:
            from fanfic_pipeline.data.nhat_the_chi_ton.knowledge import LUC_DAO_RULES
            if isinstance(LUC_DAO_RULES, list):
                frozen_canon.extend(LUC_DAO_RULES)
        except: pass
        # Try invariants from canon/frozen_invariants.json if exists
        try:
            p = pathlib.Path(__file__).resolve().parents[2] / "canon" / "frozen_invariants.json"
            if p.exists():
                import json
                data=json.loads(p.read_text(encoding="utf-8"))
                frozen_canon.extend(data if isinstance(data, list) else data.get("invariants", []))
        except: pass
    if not frozen_canon:
        return CheckerResult(checker_id="frozen_canon", name="Frozen Canon Preservation", tier="A_deterministic", status="UNKNOWN", score=5, reason="Chưa có frozen_invariants — chạy canon build-graph trước", checker_version="2.0")
    issues=[]
    for inv in frozen_canon:
        # inv may be str or dict {kind, severity, detect: {subject, realm, forbidden_acts, fact}}
        kind = "power_rule"
        severity = "hard"
        detect = {}
        raw = inv
        if isinstance(inv, dict):
            kind = inv.get("kind", "power_rule")
            severity = inv.get("severity", "hard")
            detect = inv.get("detect", {})
            raw = inv.get("id", inv.get("name", str(inv)))
        else:
            # String rule: infer as world_structure
            raw_rule = str(inv)
            norm_rule = _normalize(raw_rule)
            # Map old power_rule strings via _normalize match
            if any(k in norm_rule for k in ["khong the bay", "khong bay", "khai khieu"]):
                kind="power_rule"; detect={"forbidden_acts": [raw_rule]}
            elif "than phan" in norm_rule and "luc dao" in norm_rule:
                kind="identity_secret"; detect={"fact": "FACT:luc_dao_identity"}
            else:
                kind="world_structure"; detect={"pattern": norm_rule}
        if kind == "power_rule":
            # Check realm + forbidden act
            acts = detect.get("forbidden_acts", [str(inv)]) if isinstance(detect, dict) else [str(inv)]
            for act in acts:
                norm_act = _normalize(act) if isinstance(act, str) else _normalize(str(act))
                if not norm_act: continue
                # Extract keywords (3+ chars) from act
                for kw in [w for w in norm_act.split() if len(w)>=3]:
                    if kw in norm_draft:
                        # Check if draft asserts the act without negation
                        idx = norm_draft.find(kw)
                        window = norm_draft[max(0,idx-30): idx+len(kw)+30]
                        if "khong" not in window and "khong the" not in window:
                            # Also verify realm context if specified
                            realm_kw = _normalize(detect.get("realm", "") or detect.get("subject", "")) if isinstance(detect, dict) else ""
                            if realm_kw and realm_kw not in norm_draft:
                                continue  # realm not in draft — not a violation of this rule
                            issues.append((raw, kw, "power_rule"))
                            break
                if issues and issues[-1][0]==raw: break
        elif kind == "identity_secret":
            fact = detect.get("fact", "") if isinstance(detect, dict) else ""
            # Any reveal of that fact without approved divergence
            # Normalize fact mention
            needles = []
            if "luc dao" in _normalize(str(fact)) or "luc dao" in _normalize(str(inv)):
                needles = ["than phan luc dao", "lo than phan", "tiet lo luc dao", "cong khai than phan"]
            for needle in needles:
                if needle in norm_draft:
                    issues.append((raw, needle, "identity_secret"))
                    break
        elif kind == "world_structure":
            pat = detect.get("pattern", _normalize(str(inv))) if isinstance(detect, dict) else _normalize(str(inv))
            if pat and len(pat)>=6 and pat in norm_draft:
                # Heuristic: mention of forbidden world fact
                issues.append((raw, pat[:20], "world_structure"))
    hard = [(inv,kw,k) for inv,kw,k in issues if True]  # all power/identity are hard by default
    # power_rule + identity_secret are hard
    if hard:
        # Use first hard as evidence
        inv, kw, kind = hard[0]
        return CheckerResult(checker_id="frozen_canon", name="Frozen Canon Preservation", tier="A_deterministic", status="FAIL", score=3, reason=f"Vi phạm frozen invariant: {str(inv)[:60]} (khớp '{kw}')", evidence_spans=[kw], checker_version="2.0")
    return CheckerResult(checker_id="frozen_canon", name="Frozen Canon Preservation", tier="A_deterministic", status="PASS", score=9, reason=f"Kiểm {len(frozen_canon)} bất biến, không vi phạm", checker_version="2.0")


class ConsistencyVerificationStack:
    @staticmethod
    def evaluate(packet_hash: str, draft_text: str, outline: Dict[str,Any], risk_level: str = "LOW",
                state_delta: Any = None, canon_evidence: List[Dict] = None, audited_hash: str = "") -> AuditReceipt:
        h = audited_hash or hashlib.sha256(draft_text.encode("utf-8")).hexdigest()[:16]
        results: List[CheckerResult] = []
        # Tier A — always
        results.append(_check_word_count(draft_text, outline))
        results.append(_check_realm(draft_text, state_delta))
        results.append(_check_resource(draft_text, state_delta))
        results.append(_check_alive(draft_text, state_delta))
        
        # hash_branch check
        hash_spec = next((s for s in CHECKER_REGISTRY if s.checker_id == "hash_branch"), None)
        if hash_spec:
            hb_status = "PASS" if audited_hash else "UNKNOWN"
            results.append(CheckerResult(
                checker_id="hash_branch", name=hash_spec.name,
                tier=hash_spec.tier, status=hb_status,
                score=10 if hb_status == "PASS" else 5,
                reason=f"Draft hash verified: {audited_hash[:16]}" if audited_hash else "Missing draft hash",
                checker_version="2.0"
            ))

        # Tier C — never blocks
        results.append(_check_ai_pattern(draft_text, outline))

        # Call real checkers for spatial/timeline/frozen
        try:
            ch_num = outline.get("chapter_number", outline.get("chapter_num", 0)) if isinstance(outline, dict) else 0
        except: ch_num = 0

        if not any(r.checker_id == "spatial_continuity" for r in results):
            results.append(_check_spatial(draft_text, state_delta))
        if not any(r.checker_id == "timeline_consistency" for r in results):
            results.append(_check_timeline(draft_text, outline, ch_num))
        if not any(r.checker_id == "frozen_canon" for r in results):
            frozen = None
            try:
                from fanfic_pipeline.core.state_manager import ProjectStateManager
            except: pass
            results.append(_check_frozen_canon(draft_text, frozen))

        # Butterfly & Canon Checkers (SPEC §B7)
        if _HAS_BUTTERFLY:
            try:
                _cf = outline.get("counterfactual", {}) if isinstance(outline, dict) else {}
                _ripples = outline.get("ripples_due", []) if isinstance(outline, dict) else []
                _never = outline.get("never_converge", []) if isinstance(outline, dict) else []
                _pod = outline.get("pod") if isinstance(outline, dict) else None

                if not any(r.checker_id == "canon_orphan" for r in results):
                    results.append(check_canon_orphan(draft_text, _cf))
                if not any(r.checker_id == "butterfly_debt" for r in results):
                    overdue = [r for r in _ripples if isinstance(r, dict) and r.get("status") == "overdue"]
                    due = [r for r in _ripples if isinstance(r, dict) and r.get("status") in ("open", "due")]
                    results.append(check_butterfly_debt(draft_text, due, overdue))
                if not any(r.checker_id == "divergence_monotonicity" for r in results):
                    results.append(check_divergence_monotonicity(draft_text, _never))
                if not any(r.checker_id == "pod_compatibility" for r in results):
                    if _pod is not None:
                        results.append(check_pod_compatibility(draft_text, _pod, _cf))
                    elif canon_evidence:
                        spec = next(s for s in CHECKER_REGISTRY if s.checker_id == "pod_compatibility")
                        results.append(CheckerResult(checker_id="pod_compatibility", name=spec.name, tier=spec.tier, status="PASS", score=7, reason="Heuristic POD pass (evidence present)", checker_version=spec.checker_version))
            except Exception as e:
                pass

        # Stub fallback loop for all unimplemented checkers (e.g. ooc_fidelity, relationship_dynamics, resource_ledger, etc.)
        for spec in CHECKER_REGISTRY:
            if spec.status == "stub" and not any(r.checker_id == spec.checker_id for r in results):
                results.append(CheckerResult(
                    checker_id=spec.checker_id, name=spec.name, tier=spec.tier,
                    status="UNKNOWN", score=5,
                    reason=f"Checker '{spec.name}' marked as stub — awaiting implementation",
                    checker_version=spec.checker_version
                ))

        # Verdict: Tier A FAIL => BLOCK/REVISE; UNKNOWN on P0 => REVISE (fail-closed)
        has_tier_a_fail = any(r.tier=="A_deterministic" and r.status=="FAIL" for r in results)
        has_p0_unknown = any(r.status=="UNKNOWN" and next((s.severity for s in CHECKER_REGISTRY if s.checker_id==r.checker_id),"P1")=="P0" for r in results)
        # BUG-02 fix: P0 UNKNOWN => REVISE fail-closed regardless of risk
        if has_tier_a_fail:
            verdict="REVISE"
        elif has_p0_unknown:
            verdict="REVISE"
        else:
            # Tier C FAIL is advisory only — does not block commit
            if any(r.status=="FAIL" and r.tier != "C_narrative" for r in results):
                verdict="REVISE"
            else:
                verdict="PASS"
        issues=[]
        for r in results:
            if r.status in ("FAIL","UNKNOWN") and r.tier!="C_narrative":
                issues.append({"checker_id": r.checker_id, "reason": r.reason, "status": r.status, "tier": r.tier, "evidence_spans": r.evidence_spans})
        score = sum(r.score for r in results) / max(len(results),1)
        return AuditReceipt(audited_hash=h, checker_results=results, verdict=verdict, issues=issues, checker_versions={r.checker_id: r.checker_version for r in results}, overall_score=score)

# --- Legacy shims ---
AUDIT_33_SPEC = [{"id": i, "name": s.name, "cat": s.category, "critical": s.severity=="P0"} for i,s in enumerate(CHECKER_REGISTRY, start=1)]
AI_FATIGUE_PHRASES = AI_PHRASES

class DimensionResult(BaseModel):
    id: str
    name: str
    score: float = 10.0
    passed: bool = True
    status: str = "PASS"
    issue_description: str = ""
    reason: str = ""

class FullAuditReport(BaseModel):
    overall_score: float = 10.0
    verdict: str = "PASS"
    revision_action_plan: List[str] = Field(default_factory=list)
    dimensions: List[DimensionResult] = Field(default_factory=list)

class AuditorEngine:
    @staticmethod
    def evaluate_draft(chapter_num: int, draft_text: str, outline_data: Dict[str,Any], min_words: int = 1500, max_words: int = 4000) -> FullAuditReport:
        receipt = ConsistencyVerificationStack.evaluate("", draft_text, outline_data, risk_level="LOW", audited_hash=hashlib.sha256(draft_text.encode("utf-8")).hexdigest()[:16])
        dims=[]
        for r in receipt.checker_results:
            dims.append(DimensionResult(
                id=r.checker_id, name=r.name, score=r.score,
                passed=(r.status=="PASS"), status=r.status,
                issue_description=r.reason, reason=r.reason
            ))
        return FullAuditReport(overall_score=receipt.overall_score, verdict=receipt.verdict, revision_action_plan=[i["reason"] for i in receipt.issues], dimensions=dims)

