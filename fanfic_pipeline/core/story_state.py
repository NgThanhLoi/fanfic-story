"""
Structured Story State & Closed-Loop State Extractor (FR-08, FR-18 Compliant) v1.1
- Tracks per-character realm, location, injury, inventory, resources, statuses
- Extracts StateDelta with evidence_locators + old/new values
- Validates transitions: monotonic realm, resource >=0, inventory ownership etc.
- TransitionValidator (7 validators), RiskProfiler, EvidenceLedger
"""
import re
import copy
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Literal
from pydantic import BaseModel, Field

REALM_ORDER: Dict[str, int] = {
    "Khai Khiếu (Sơ kỳ)": 10, "Khai Khiếu (Trung kỳ)": 11, "Khai Khiếu (Hậu kỳ)": 12,
    "Khai Khiếu": 10, "Khai Khiếu cảnh": 10, "Cửu Khiếu": 10, "Tề Khiếu": 12,
    "Ngoại Cảnh": 20, "Ngoại Cảnh (Nhất Trọng Thiên)": 21, "Ngoại Cảnh (Nhị Trọng Thiên)": 22,
    "Ngoại Cảnh cảnh": 20, "Thiên Nhân Hợp Nhất": 20, "Cửu Trọng Thiên": 28,
    "Pháp Thân": 30, "Nhân Tiên": 30, "Địa Tiên": 31, "Thiên Tiên": 32,
    "Bỉ Ngạn": 40, "Đạo Quả": 40,
}
def _realm_rank(r: str) -> int:
    if not r: return -1
    if r in REALM_ORDER: return REALM_ORDER[r]
    rl = r.lower()
    for k, v in REALM_ORDER.items():
        if k.lower() in rl or rl in k.lower(): return v
    return -1

class CharacterStateRecord(BaseModel):
    character_id: str
    name: str
    realm: str = "Khai Khiếu (Sơ kỳ)"
    location: str = "Không gian Lục Đạo Luân Hồi"
    injuries: List[str] = Field(default_factory=list)
    inventory: List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)
    thien_cong: int = 100
    statuses: List[str] = Field(default_factory=list)
    alive: bool = True

class StateDelta(BaseModel):
    chapter_number: int
    location_change: Optional[str] = None
    thien_cong_changes: Dict[str, int] = Field(default_factory=dict)
    items_acquired: Dict[str, List[str]] = Field(default_factory=dict)
    items_consumed: Dict[str, List[str]] = Field(default_factory=dict)
    injuries_sustained: Dict[str, List[str]] = Field(default_factory=dict)
    injuries_healed: Dict[str, List[str]] = Field(default_factory=dict)
    realm_advancements: Dict[str, str] = Field(default_factory=dict)
    relationship_updates: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_spans: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    old_values: Dict[str, Any] = Field(default_factory=dict)
    new_values: Dict[str, Any] = Field(default_factory=dict)
    evidence_locators: List[Dict[str, Any]] = Field(default_factory=list)
    inference_type: Literal["extracted", "inferred"] = "extracted"
    alive_changes: Dict[str, bool] = Field(default_factory=dict)

# ---------------------------------------------------------------------------
class TransitionValidator:
    @staticmethod
    def validate_realm_transition(old: str, new: str) -> bool:
        if not old or not new or old == new: return True
        return _realm_rank(new) >= _realm_rank(old)
    # alias for compat
    @staticmethod
    def validate_realm(old: str, new: str) -> Tuple[bool, str]:
        ok = TransitionValidator.validate_realm_transition(old, new)
        return ok, "" if ok else f"Realm downgrade {old}->{new}"
    @staticmethod
    def validate_resource(delta: StateDelta, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        tc = state.get("team_thien_cong", {})
        for ch, chg in delta.thien_cong_changes.items():
            cur = tc.get(ch, 100)
            if cur + chg < 0: errors.append(f"Thiện công {ch} âm ({cur}+{chg}={cur+chg})")
        return len(errors)==0, errors
    @staticmethod
    def validate_location(delta_or_loc, state: Optional[Dict]=None) -> Tuple[bool, List[str]]:
        # supports both signatures: validate_location(delta, state) and validate_location(new_loc, state)
        if isinstance(delta_or_loc, StateDelta):
            if delta_or_loc.location_change and len(delta_or_loc.location_change)>200:
                return False, ["location_change quá dài"]
            return True, []
        if isinstance(delta_or_loc, str):
            if delta_or_loc and len(delta_or_loc)>200: return False, ["location quá dài"]
            return True, []
        return True, []
    @staticmethod
    def validate_inventory(delta: StateDelta, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        invs = state.get("character_inventories", {})
        flat = state.get("inventory", [])
        for ch, items in delta.items_consumed.items():
            owned = invs.get(ch, []) + flat
            owned_lower=[x.lower() for x in owned]
            for it in items:
                if it.lower() not in owned_lower and not any(it.lower() in o for o in owned_lower):
                    if "thiện công" not in it.lower() and "linh thạch" not in it.lower():
                        errors.append(f"{ch} tiêu hao '{it}' nhưng không sở hữu (kho: {owned})")
        return len(errors)==0, errors
    @staticmethod
    def validate_injury(delta: StateDelta, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        inj = state.get("character_injuries", {})
        for ch, healed in delta.injuries_healed.items():
            existing = inj.get(ch, []) + state.get("injuries", [])
            el=[x.lower() for x in existing]
            for h in healed:
                if h.lower() not in el and not any(h.lower() in e for e in el):
                    if existing:  # only error if there was some injury list
                        errors.append(f"{ch} chữa '{h}' nhưng không có thương tích này (hiện có: {existing})")
                    else:
                        # if no injuries at all, healing without injury is suspicious but allow if draft says so? Mark error
                        errors.append(f"{ch} không có thương tích để chữa '{h}'")
        return len(errors)==0, errors
    @staticmethod
    def validate_alive_status(delta: StateDelta, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        statuses = state.get("character_statuses", {})
        alive_map = state.get("character_alive", {})
        dead=set()
        for ch, sts in statuses.items():
            if isinstance(sts, list):
                for s in sts:
                    if any(k in s.lower() for k in ["dead","đã chết","tử vong","vong mạng"]): dead.add(ch)
            elif isinstance(sts, str) and any(k in sts.lower() for k in ["dead","đã chết","tử vong"]):
                dead.add(ch)
        for ch in list(alive_map.keys()):
            if alive_map.get(ch) is False: dead.add(ch)
        for ch in list(delta.thien_cong_changes.keys())+list(delta.items_acquired.keys())+list(delta.realm_advancements.keys()):
            if ch in dead: errors.append(f"{ch} đã chết nhưng vẫn có thay đổi trạng thái")
        for ch, v in delta.alive_changes.items():
            if ch in dead and not v: errors.append(f"{ch} đã chết, không thể chết lần nữa")
        return len(errors)==0, errors
    # alias
    @staticmethod
    def validate_alive(delta: StateDelta, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        return TransitionValidator.validate_alive_status(delta, state)
    @staticmethod
    def validate_thien_cong(delta: StateDelta, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        return TransitionValidator.validate_resource(delta, state)
    @staticmethod
    def validate_realm_monotonic(delta: StateDelta, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        realms = state.get("character_realms", {})
        if not realms and "characters" in state:
            for c in state.get("characters", []):
                if isinstance(c, dict) and "name" in c and "realm" in c: realms[c["name"]]=c["realm"]
        for ch, new_r in delta.realm_advancements.items():
            old_r = realms.get(ch, "Khai Khiếu (Sơ kỳ)")
            if not TransitionValidator.validate_realm_transition(old_r, new_r):
                errors.append(f"Cảnh giới thụt lùi: {ch} {old_r}->{new_r}")
        return len(errors)==0, errors
    @staticmethod
    def validate_knowledge(delta: StateDelta, knowledge_state: Dict) -> Tuple[bool, List[str]]:
        return True, []
    @staticmethod
    def validate_relationship(delta: StateDelta, state: Dict) -> Tuple[bool, List[str]]:
        errs=[]
        for ru in delta.relationship_updates:
            if abs(ru.get("delta",0))>5 and not ru.get("evidence_span"):
                errs.append(f"Relationship jump too large without evidence: {ru}")
        return len(errs)==0, errs
    @staticmethod
    def validate_beat_postconditions(beat: Dict, delta: StateDelta) -> Tuple[bool, List[str]]:
        errs=[]
        for post in beat.get("postconditions",[]):
            if "realm" in post.lower() and not delta.realm_advancements:
                errs.append(f"Beat postcondition not met: {post}")
        return len(errs)==0, errs
    @staticmethod
    def validate_all(delta: StateDelta, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        fns=[TransitionValidator.validate_resource, TransitionValidator.validate_location, TransitionValidator.validate_inventory, TransitionValidator.validate_injury, TransitionValidator.validate_alive_status, TransitionValidator.validate_realm_monotonic]
        all_errs=[]
        for fn in fns:
            ok, errs = fn(delta, state)
            all_errs.extend(errs)
        return len(all_errs)==0, all_errs

class RiskProfiler:
    @staticmethod
    def compute_risk(delta: StateDelta, draft_text: str) -> Dict[str, Any]:
        score=0; triggers=[]
        if delta.realm_advancements: score+=40; triggers.append(f"realm_advancement: {delta.realm_advancements}")
        if delta.alive_changes: score+=50; triggers.append(f"death/alive change: {delta.alive_changes}")
        if delta.items_acquired or delta.items_consumed: score+=15; triggers.append(f"item change acquired={delta.items_acquired} consumed={delta.items_consumed}")
        if delta.thien_cong_changes:
            for ch, chg in delta.thien_cong_changes.items():
                if abs(chg)>=500: score+=20; triggers.append(f"Thiện công lớn {ch} {chg:+d}")
                elif abs(chg)>=150: score+=10; triggers.append(f"Thiện công {ch} {chg:+d}")
                else: score+=5; triggers.append(f"Thiện công {ch} {chg:+d}")
        if delta.injuries_sustained: score+=15; triggers.append(f"injuries {delta.injuries_sustained}")
        if len(delta.relationship_updates)>0: score+=20; triggers.append(f"relationship change x{len(delta.relationship_updates)}")
        low = draft_text.lower()
        if any(k in low for k in ["bí mật","thân phận","tố nữ","vô sinh"]): score+=10; triggers.append("secret reveal signal")
        if "đột phá" in low or "pháp thân" in low: score+=15; triggers.append("cultivation breakthrough signal")
        if any(k in low for k in ["tử vong","đã chết","giết chết"]): score+=30; triggers.append("death signal in text")
        score=min(100,score)
        if score>=76: level="CRITICAL"
        elif score>=51: level="HIGH"
        elif score>=26: level="MEDIUM"
        else: level="LOW"
        if not triggers: triggers.append("Không có biến động đáng kể")
        return {"level": level, "score": score, "triggers": triggers}

class EvidenceLedger:
    @staticmethod
    def locate_issues(draft_text: str, claims: List[Any]) -> List[Dict[str, Any]]:
        # claims may be List[str] or List[Dict]
        issues=[]
        norm_claims=[]
        if not claims:
            sents = re.split(r'[。\.!\?！\n]+', draft_text)
            kws=["cảnh giới","khai khiếu","ngoại cảnh","pháp thân","bỉ ngạn","thiện công","lục đạo","tố nữ","bát cửu","như lai","tiệt thiên","đột phá","tử vong","đã chết","chữa lành","tiêu hao"]
            norm_claims=[s.strip() for s in sents if any(k in s.lower() for k in kws) and len(s.strip())>10]
        else:
            for c in claims:
                if isinstance(c, dict): norm_claims.append(c.get("claim","") or c.get("text","") or str(c))
                else: norm_claims.append(str(c))
        for i, claim in enumerate(norm_claims):
            claim=claim.strip()
            if not claim: continue
            pos=draft_text.find(claim)
            if pos==-1:
                head=claim[:20]
                pos=draft_text.find(head)
                span=draft_text[pos:pos+len(claim)+40] if pos!=-1 else claim[:120]
            else:
                span=draft_text[max(0,pos-20):pos+len(claim)+40]
            issues.append({"issue_id": f"ISSUE_{i+1:03d}", "claim": claim, "draft_span": span.strip().replace("\n"," "), "draft_offset": pos if pos!=-1 else -1, "canon_evidence": None, "state_evidence": None, "reason": "Chưa đối chiếu", "confidence": 0.5, "severity": "P1", "checker_id": "evidence_ledger"})
        # if claims were List[Dict] with explicit structure, also handle direct passthrough
        if claims and isinstance(claims[0], dict) and "claim" in claims[0]:
            # already handled above, but preserve extra fields
            for idx, c in enumerate(claims):
                if idx < len(issues):
                    for k in ["reason","confidence","severity","checker_id"]:
                        if k in c: issues[idx][k]=c[k]
        return issues
    @staticmethod
    def verify_evidence(issues: List[Dict[str, Any]], canon_evidence: List[Dict[str, Any]], state_evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
        enriched=[]
        for iss in issues:
            claim_low=iss["claim"].lower()
            best=None; best_score=0
            for ce in canon_evidence or []:
                text=(ce.get("text") or ce.get("content") or ce.get("description_vi") or "")+" "+(ce.get("title") or "")
                overlap=len(set(claim_low.split()) & set(text.lower().split()))
                if overlap>best_score: best_score=overlap; best=ce
            state_hit=None
            state_str=str(state_evidence).lower() if state_evidence else ""
            if any(tok in state_str for tok in claim_low.split() if len(tok)>2):
                state_hit={"matched": True, "state_snapshot": str(state_evidence)[:500]}
            if best and best_score>=2:
                reason=f"Tìm thấy bằng chứng canon (overlap={best_score}) hỗ trợ claim"
                conf=min(0.9, 0.5+best_score*0.1)
            elif best and best_score==1:
                reason="Bằng chứng canon yếu, cần kiểm chứng thêm"; conf=0.55
            else:
                reason="Không tìm thấy bằng chứng canon trực tiếp"; conf=0.35
            enriched.append({**iss, "canon_evidence": best, "state_evidence": state_hit, "reason": reason, "confidence": round(conf,2)})
        return enriched

class StoryStateManager:
    _KNOWN_ITEMS=["Lệnh bài Tố Nữ Đạo","Lệnh bài","Hoa sen máu","Đan dược","Bồi Nguyên Đan","Giải Độc Đan","Thiện công","Linh thạch","Phù chú","Ngọc giản","Bí kíp","Trường đao","Nhuyễn kiếm","Cổ cầm Phượng Tê"]
    _REALM_KWS=["Khai Khiếu","Ngoại Cảnh","Pháp Thân","Bỉ Ngạn","Cửu Khiếu","Tề Khiếu","Nhất Trọng Thiên","Nhị Trọng Thiên","Tam Trọng Thiên","Cửu Trọng Thiên","Địa Tiên","Thiên Tiên","Đạo Quả"]
    @staticmethod
    def _add_locator(delta: StateDelta, field: str, span_text: str, char_offset: int):
        delta.evidence_locators.append({"field": field, "span_text": span_text.strip(), "char_offset": char_offset})
        if span_text.strip() not in delta.evidence_spans:
            delta.evidence_spans.append(span_text.strip())
    @staticmethod
    def extract_state_delta(chapter_num: int, draft_text: str, current_state: Dict[str, Any]) -> StateDelta:
        delta = StateDelta(chapter_number=chapter_num)
        text_lower = draft_text.lower()
        old_values: Dict[str, Any] = {}
        new_values: Dict[str, Any] = {}
        cur_loc = current_state.get("current_location","Không gian Lục Đạo Luân Hồi")
        old_values["location"]=cur_loc
        # 1. Location
        loc_found=None; loc_span=""; loc_offset=-1
        patterns=[(r"sơn đạo| rút lui |rời khỏi sơn trại|đường rút lui","Sơn đạo Ẩn Hình phường - Đường rút lui","Rút lui khỏi sơn trại trên sơn đạo"),(r"mật thất","Mật thất Ẩn Hình sơn trại","Tiến sâu vào mật thất phía sau sơn trại"),(r"quảng trường|lục đạo luân hồi.*quảng trường","Quảng trường Lục Đạo Luân Hồi","Quảng trường Lục Đạo Luân Hồi"),(r"ẩn hình phường|phường thị","Ẩn Hình phường","Ẩn Hình phường")]
        for pat, loc_name, evidence in patterns:
            m=re.search(pat, text_lower)
            if m:
                loc_found=loc_name; loc_span=draft_text[m.start():m.end()+40].strip().split("\n")[0]; loc_offset=m.start(); break
        if loc_found:
            delta.location_change=loc_found
            StoryStateManager._add_locator(delta,"location_change",loc_span,loc_offset)
            new_values["location"]=loc_found
        # 2. Thien cong — BUG-06 fix: dedupe per span (longest match), only one reward per sentence
        tc_spans = []  # list of (start, end, amount, span_text)
        for pat, amount in [(r"hoàn thành nhiệm vụ|nhận được thiện công|thưởng thiện công",150),(r"khấu trừ thiện công|tiêu hao thiện công|mất\s+\d+\s*thiện công",-50)]:
            for m in re.finditer(pat, text_lower):
                tc_spans.append((m.start(), m.end(), pat, amount, m.group(0)))
        # Also numeric patterns
        for m in re.finditer(r"(\+|\-)?\s*(\d+)\s*thiện công", text_lower):
            # skip if already inside a longer span
            if any(s<=m.start() and m.end()<=e for s,e,_,_,_ in tc_spans): continue
            val=int(m.group(2))
            if m.group(1)=="-": val=-val
            elif m.group(1) is None and "tiêu hao" in draft_text[max(0,m.start()-30):m.end()].lower(): val=-val
            else:
                if tc_spans: continue
            tc_spans.append((m.start(), m.end(), "numeric", val, m.group(0)))
        # Dedupe overlapping: sort by start, keep longest, drop contained spans
        tc_spans.sort(key=lambda x: (x[0], -x[1]))
        filtered=[]
        occupied=set()
        for start,end,pat,amt,raw in tc_spans:
            if any(i in occupied for i in range(start,end)): continue
            # Also sentence-level dedupe: one thien_cong per sentence (keep first)
            sent_start = text_lower.rfind("。", 0, start)
            sent_end = text_lower.find("。", end)
            sent_key = (sent_start, sent_end if sent_end!=-1 else end+80)
            # sentence dedup handled below via abs(start-fs)<120 equivalent
            # One thien_cong per sentence (split by 。！？.!?\n) — dedupe within same sentence
            # Find sentence boundaries for current start
            sent_idx = text_lower[:start].count("。") + text_lower[:start].count("\n") + text_lower[:start].count("！")
            if any((text_lower[:fs].count("。")+text_lower[:fs].count("\n")+text_lower[:fs].count("！"))==sent_idx for fs,fe,_,_,_ in filtered):
                continue
            filtered.append((start,end,pat,amt,raw))
            for i in range(start,end): occupied.add(i)
        # Now emit one change per filtered span
        for start,end,pat,amt,raw in filtered:
            if pat=="numeric":
                delta_amount=amt
                span_text=raw
            else:
                num_m=re.search(r"(\d+)\s*thiện công", draft_text[start:end+30].lower())
                delta_amount=int(num_m.group(1)) if num_m else amt
                if "khấu trừ" in pat or "tiêu hao" in pat or "mất" in pat: delta_amount=-abs(delta_amount)
                span_text=draft_text[start:end+30].strip().split("\n")[0]
                # Use actual substring as evidence
                span_text=draft_text[start:end].strip()
            chars=["Mạnh Kỳ"]
            # Only add second char if explicitly near
            if "giang chỉ vi" in text_lower[max(0,start-200):end+200]:
                # Only if sentence mentions both
                if "giang" in draft_text[max(0,start-80):end+80].lower():
                    chars.append("Giang Chỉ Vi")
            for c in chars:
                delta.thien_cong_changes[c]=delta.thien_cong_changes.get(c,0)+delta_amount
            # Evidence must be substring of draft
            evidence = draft_text[start:end].strip()
            StoryStateManager._add_locator(delta,"thien_cong_changes",evidence,start)
            old_values.setdefault("thien_cong",{})[chars[0]]=current_state.get("team_thien_cong",{}).get(chars[0],100)
            new_values.setdefault("thien_cong",{})[chars[0]]=old_values["thien_cong"][chars[0]]+delta_amount
        # 3. Items acquired — BUG-06 fix: longest-match, no substring child, evidence is Draft substring
        acquire_triggers=["thu được","nhận được","đoạt được","thu thập","nhặt được","chiếm được","lấy được"]
        # Sort known items by length desc for longest-match
        # Resource items handled by thien_cong, not as inventory
        _RESOURCE_AS_ITEM = {"Thiện công", "Linh thạch"}
        sorted_items = sorted([x for x in StoryStateManager._KNOWN_ITEMS if x not in _RESOURCE_AS_ITEM], key=len, reverse=True)
        acquired_spans = []  # occupied char ranges to avoid child
        for item in sorted_items:
            il=item.lower()
            if il in text_lower:
                for acq in acquire_triggers:
                    for m in re.finditer(re.escape(acq), text_lower):
                        ws=max(0,m.start()-80); we=m.end()+120
                        window=text_lower[ws:we]
                        if il in window:
                            # longest-match: skip if any already acquired item is superstring of this in same window
                            already = [it for lst in delta.items_acquired.values() for it in lst]
                            if any(item.lower() in it.lower() and item.lower()!=it.lower() for it in already):
                                continue
                            # span dedup + window dedup: one item per acquire trigger occurrence
                            it_start = window.find(il) + ws
                            it_end = it_start + len(item)
                            # if same acquire trigger word already yielded an item, skip smaller child in same window
                            # acquired_spans tracks (acq_m.start, acq_m.end+120) windows already used
                            if any(abs(m.start()-s)<100 for s,e in acquired_spans):
                                # Same window already produced an item — only keep if new is strictly longer and not substring child
                                continue
                            # Also skip if item chars overlap already occupied item chars
                            if any(s<=it_start and it_end<=e for s,e in acquired_spans): continue
                            char="Mạnh Kỳ"
                            for cand in ["mạnh kỳ","giang chỉ vi","tề chính ngôn","nguyễn ngọc thư","cố tiểu tang"]:
                                if cand in window:
                                    mapping={"mạnh kỳ":"Mạnh Kỳ","giang chỉ vi":"Giang Chỉ Vi","tề chính ngôn":"Tề Chính Ngôn","nguyễn ngọc thư":"Nguyễn Ngọc Thư","cố tiểu tang":"Cố Tiểu Tang"}
                                    char=mapping[cand]; break
                            delta.items_acquired.setdefault(char,[])
                            if item not in delta.items_acquired[char]:
                                # Remove child items already there that are substrings of new (longer) item
                                delta.items_acquired[char] = [x for x in delta.items_acquired[char] if x.lower() not in item.lower() or x.lower()==item.lower()]
                                # Prune if new is substring of already longer
                                if any(item.lower() in x.lower() and item.lower()!=x.lower() for x in delta.items_acquired[char]):
                                    continue
                                delta.items_acquired[char].append(item)
                                evidence = draft_text[m.start():m.end()+len(item)+20].strip().split("\n")[0]
                                # Ensure substring of draft
                                if evidence not in draft_text: evidence = draft_text[ws:we].strip()[:60]
                                StoryStateManager._add_locator(delta,"items_acquired",evidence,m.start())
                                acquired_spans.append((m.start(), m.end()+100))
                                old_values.setdefault("inventory",{})[char]=list(current_state.get("character_inventories",{}).get(char,[]))
                                new_values.setdefault("inventory",{})[char]=old_values["inventory"][char]+[item]
        if "lệnh bài" in text_lower and ("tố nữ" in text_lower or "hoa sen" in text_lower or "cố tiểu tang" in text_lower):
            # Only if not already acquired longer
            if not any("lệnh bài" in it.lower() for lst in delta.items_acquired.values() for it in lst):
                delta.items_acquired.setdefault("Mạnh Kỳ",[])
                delta.items_acquired["Mạnh Kỳ"].append("Lệnh bài Tố Nữ Đạo")
                # Find actual draft substring as evidence, not fabricated sentence
                m=re.search(r"lệnh bài[^\n]{0,30}", text_lower)
                evidence = draft_text[m.start():m.end()].strip() if m else "lệnh bài"
                StoryStateManager._add_locator(delta,"items_acquired",evidence,m.start() if m else 0)
        # 4. Items consumed
        consume_triggers=["dùng","tiêu hao","sử dụng","nuốt","uống","phục dụng","tiêu tốn","hao tổn"]
        for item in StoryStateManager._KNOWN_ITEMS:
            il=item.lower()
            if il in text_lower:
                for cons in consume_triggers:
                    for m in re.finditer(re.escape(cons), text_lower):
                        ws=max(0,m.start()-30); we=m.end()+120
                        window=text_lower[ws:we]
                        if il in window:
                            char="Mạnh Kỳ"
                            for cand in ["mạnh kỳ","giang chỉ vi","tề chính ngôn","nguyễn ngọc thư"]:
                                if cand in window:
                                    mapping={"mạnh kỳ":"Mạnh Kỳ","giang chỉ vi":"Giang Chỉ Vi","tề chính ngôn":"Tề Chính Ngôn","nguyễn ngọc thư":"Nguyễn Ngọc Thư"}
                                    char=mapping[cand]; break
                            delta.items_consumed.setdefault(char,[])
                            if item not in delta.items_consumed[char]:
                                delta.items_consumed[char].append(item)
                                StoryStateManager._add_locator(delta,"items_consumed",f"{cons} {item}",m.start())
                                old_values.setdefault("consumed_inventory",{})[char]=list(current_state.get("character_inventories",{}).get(char,[]))
                                new_values.setdefault("consumed_inventory",{})[char]=[x for x in old_values["consumed_inventory"][char] if x!=item]
        # fallback generic dan
        if any(k in text_lower for k in ["dùng","tiêu hao","nuốt","uống"]) and "đan" in text_lower and not delta.items_consumed:
            # simple fallback
            for m in re.finditer(r"dùng[^\n]{0,30}đan|tiêu hao[^\n]{0,30}đan", text_lower):
                delta.items_consumed.setdefault("Mạnh Kỳ",[])
                if "Đan dược hồi phục" not in delta.items_consumed["Mạnh Kỳ"]:
                    delta.items_consumed["Mạnh Kỳ"].append("Đan dược hồi phục")
                    StoryStateManager._add_locator(delta,"items_consumed","Dùng đan dược hồi phục",m.start())
        # 5. Injuries sustained
        injury_keywords=["thương tích","trúng đao","hộc máu","trọng thương","khí huyết chấn động","nội thương","gãy xương"]
        for kw in injury_keywords:
            for m in re.finditer(re.escape(kw), text_lower):
                window=text_lower[max(0,m.start()-100):m.end()+100]
                char="Mạnh Kỳ"
                for cand in ["mạnh kỳ","giang chỉ vi","tề chính ngôn","nguyễn ngọc thư"]:
                    if cand in window:
                        mapping={"mạnh kỳ":"Mạnh Kỳ","giang chỉ vi":"Giang Chỉ Vi","tề chính ngôn":"Tề Chính Ngôn","nguyễn ngọc thư":"Nguyễn Ngọc Thư"}
                        char=mapping[cand]; break
                delta.injuries_sustained.setdefault(char,[])
                inj_name=kw.title() if kw!="hộc máu" else "Khí huyết chấn động nhẹ"
                if inj_name=="Hộc Máu": inj_name="Khí huyết chấn động nhẹ"
                if inj_name not in delta.injuries_sustained[char]:
                    delta.injuries_sustained[char].append(inj_name)
                    StoryStateManager._add_locator(delta,"injuries_sustained",kw,m.start())
        # 6. Injuries healed
        heal_triggers=["chữa lành","hồi phục","khỏi hẳn","lành lại","thương thế đã lành","vết thương khép lại","hồi phục thương thế","chữa trị","lành vết thương"]
        for ht in heal_triggers:
            for m in re.finditer(re.escape(ht), text_lower):
                window=text_lower[max(0,m.start()-100):m.end()+100]
                char="Mạnh Kỳ"
                for cand in ["mạnh kỳ","giang chỉ vi","tề chính ngôn","nguyễn ngọc thư"]:
                    if cand in window:
                        mapping={"mạnh kỳ":"Mạnh Kỳ","giang chỉ vi":"Giang Chỉ Vi","tề chính ngôn":"Tề Chính Ngôn","nguyễn ngọc thư":"Nguyễn Ngọc Thư"}
                        char=mapping[cand]; break
                inj_name="Khí huyết chấn động nhẹ"
                for kw in injury_keywords:
                    if kw in window: inj_name=kw.title(); break
                delta.injuries_healed.setdefault(char,[])
                if inj_name not in delta.injuries_healed[char]:
                    delta.injuries_healed[char].append(inj_name)
                    StoryStateManager._add_locator(delta,"injuries_healed",ht,m.start())
        # 7. Realm advancements
        advancement_triggers=["đột phá","tấn thăng","đả thông","thăng cấp","phá cảnh","tiến giai","đột phá đến","đột phá lên"]
        for trig in advancement_triggers:
            for m in re.finditer(re.escape(trig), text_lower):
                window=draft_text[m.start():m.end()+80]; window_lower=window.lower()
                for realm_kw in StoryStateManager._REALM_KWS:
                    if realm_kw.lower() in window_lower:
                        pre=text_lower[max(0,m.start()-120):m.end()]
                        char="Mạnh Kỳ"
                        for cand in ["mạnh kỳ","giang chỉ vi","tề chính ngôn","nguyễn ngọc thư"]:
                            if cand in pre:
                                mapping={"mạnh kỳ":"Mạnh Kỳ","giang chỉ vi":"Giang Chỉ Vi","tề chính ngôn":"Tề Chính Ngôn","nguyễn ngọc thư":"Nguyễn Ngọc Thư"}
                                char=mapping[cand]; break
                        new_realm=realm_kw
                        full_m=re.search(r"(Khai Khiếu|Ngoại Cảnh|Pháp Thân|Bỉ Ngạn)[^\n，,。]{0,20}", window)
                        if full_m: new_realm=full_m.group(0).strip()
                        delta.realm_advancements[char]=new_realm
                        StoryStateManager._add_locator(delta,"realm_advancements",f"{trig} {new_realm}",m.start())
                        old_values.setdefault("realm",{})[char]=current_state.get("character_realms",{}).get(char,"Khai Khiếu (Sơ kỳ)")
                        new_values.setdefault("realm",{})[char]=new_realm
                        break
        # 8. Relationship updates
        rel_keywords=["tin tưởng","đề phòng","thân mật","xa cách","cảm kích","hiềm khích"]
        for kw in rel_keywords:
            if kw in text_lower:
                for m in re.finditer(re.escape(kw), text_lower):
                    window=text_lower[max(0,m.start()-150):m.end()+50]
                    present=[]
                    for cand in ["mạnh kỳ","giang chỉ vi","tề chính ngôn","nguyễn ngọc thư","cố tiểu tang"]:
                        if cand in window: present.append(cand)
                    if len(present)>=2:
                        delta.relationship_updates.append({"characters": present[:2], "keyword": kw, "description": f"Quan hệ {present[0]} - {present[1]}: {kw}", "offset": m.start()})
                        StoryStateManager._add_locator(delta,"relationship_updates",kw,m.start())
        # confidence
        if len(delta.evidence_locators)>=4: delta.confidence=0.92; delta.inference_type="extracted"
        elif len(delta.evidence_locators)>=2: delta.confidence=0.78; delta.inference_type="extracted"
        elif len(delta.evidence_locators)==1: delta.confidence=0.6; delta.inference_type="extracted"
        else: delta.confidence=0.35; delta.inference_type="inferred"
        # --- BUG-06 post-validation: evidence must be Draft substring ---
        valid_spans=[]
        for ev in list(delta.evidence_spans):
            if ev.strip() and ev.strip() in draft_text:
                valid_spans.append(ev)
            elif ev.strip():
                # fabricated -> drop and mark inferred
                delta.inference_type="inferred"
                delta.confidence=min(delta.confidence, 0.5)
        delta.evidence_spans=valid_spans
        # Sync locators
        delta.evidence_locators=[loc for loc in delta.evidence_locators if loc.get("span_text","").strip() in draft_text]
        if not delta.evidence_spans and delta.evidence_locators:
            delta.evidence_spans=[loc["span_text"] for loc in delta.evidence_locators]
        if not delta.evidence_spans and (delta.thien_cong_changes or delta.items_acquired or delta.items_consumed):
            delta.inference_type="inferred"; delta.confidence=min(delta.confidence, 0.5)
        delta.old_values=old_values
        delta.new_values=new_values
        if not delta.evidence_spans and delta.evidence_locators:
            delta.evidence_spans=[loc["span_text"] for loc in delta.evidence_locators]
        return delta
    @staticmethod
    def apply_delta(current_state: Dict[str, Any], delta: StateDelta) -> Dict[str, Any]:
        updated=copy.deepcopy(current_state)
        if delta.location_change: updated["current_location"]=delta.location_change
        team_tc=dict(updated.get("team_thien_cong",{}))
        for ch, amt in delta.thien_cong_changes.items(): team_tc[ch]=team_tc.get(ch,100)+amt
        updated["team_thien_cong"]=team_tc
        char_invs=copy.deepcopy(updated.get("character_inventories",{}))
        for ch, items in delta.items_acquired.items():
            if ch not in char_invs: char_invs[ch]=[]
            for it in items:
                if it not in char_invs[ch]: char_invs[ch].append(it)
        for ch, items in delta.items_consumed.items():
            if ch not in char_invs: char_invs[ch]=[]
            for it in items:
                if it in char_invs[ch]: char_invs[ch].remove(it)
                else:
                    lower_map={x.lower(): x for x in char_invs[ch]}
                    if it.lower() in lower_map: char_invs[ch].remove(lower_map[it.lower()])
        updated["character_inventories"]=char_invs
        if "inventory" in updated:
            flat=list(updated["inventory"])
            for items in delta.items_acquired.values():
                for it in items:
                    if it not in flat: flat.append(it)
            for items in delta.items_consumed.values():
                for it in items:
                    if it in flat: flat.remove(it)
            updated["inventory"]=flat
        char_inj=copy.deepcopy(updated.get("character_injuries",{}))
        for ch, lst in delta.injuries_sustained.items():
            if ch not in char_inj: char_inj[ch]=[]
            for inj in lst:
                if inj not in char_inj[ch]: char_inj[ch].append(inj)
        for ch, healed in delta.injuries_healed.items():
            if ch not in char_inj: char_inj[ch]=[]
            for h in healed:
                if h in char_inj[ch]: char_inj[ch].remove(h)
                else:
                    lower_map={x.lower(): x for x in char_inj[ch]}
                    if h.lower() in lower_map: char_inj[ch].remove(lower_map[h.lower()])
        updated["character_injuries"]=char_inj
        char_realms=dict(updated.get("character_realms",{}))
        for ch, nr in delta.realm_advancements.items(): char_realms[ch]=nr
        if char_realms: updated["character_realms"]=char_realms
        if "characters" in updated and isinstance(updated["characters"], list):
            for c in updated["characters"]:
                if isinstance(c, dict) and c.get("name") in delta.realm_advancements:
                    c["realm"]=delta.realm_advancements[c["name"]]
        if delta.relationship_updates:
            rels=list(updated.get("relationship_updates",[])); rels.extend(delta.relationship_updates); updated["relationship_updates"]=rels
        alive=dict(updated.get("character_alive",{}))
        for ch, v in delta.alive_changes.items(): alive[ch]=v
        if alive: updated["character_alive"]=alive
        return updated
    @staticmethod
    def validate_delta(delta: StateDelta, current_state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        return TransitionValidator.validate_all(delta, current_state)
