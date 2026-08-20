# Fanfic Pipeline v2.0 — Incremental Hardening Design Spec

**Date:** 2026-08-20
**Status:** Draft — Pending User Review
**Approach:** Incremental Hardening (Approach C)
**Target:** Nền tảng vững cho fanfic 700-1000+ chương, tối ưu cho 一世之尊 trước, universal sau

---

## 1. Bối Cảnh & Mục Tiêu

### 1.1 Hiện trạng

Pipeline `fanfic_pipeline_v2.0_M1_ready` có nền móng kỹ thuật vững (EPUB ingestion, FTS5 search, sealed packet, atomic transaction, hybrid memory, alias system) nhưng audit code-level phát hiện **12 lỗ hổng nghiêm trọng**:

- 6 bugs logic (butterfly engine ngắt kết nối, checker giả mạo, epistemic logic sai)
- Data layer chỉ cover 1% scope tiểu thuyết (5/hàng trăm nhân vật, arcs cho 10/1000 chương)
- Style system không tồn tại
- Canon graph O(N²) không scale

### 1.2 Mục tiêu

1. Pipeline có thể viết fanfic 700-1000+ chương cho 一世之尊 với chất lượng nhất quán
2. Butterfly Effect Engine hoạt động end-to-end (đổi → lan truyền → sinh nợ → trả nợ → audit)
3. Văn phong biến thiên theo loại cảnh và giai đoạn truyện
4. Audit system thật sự bắt lỗi, không có checker giả mạo
5. Scale: Canon graph + enrichment store xử lý 10k+ events trong < 60 giây

### 1.3 Quyết định thiết kế

| Yếu tố | Quyết định |
|---|---|
| Quy mô | 700-1000+ chương |
| Nguyên tác | 一世之尊 (1409 chương) → universal sau |
| Enrichment | Hybrid: auto cấu trúc, semi-auto ngữ nghĩa |
| LLM | Qwen 3.8 Max / GLM 5.2 / DeepSeek V4 / Muse Spark qua CLIProxyAPI |
| Workflow | HITL cho arc mở + climax + POD; auto cho chuyển tiếp |

### 1.4 Phân chia Phase

```
Phase 0 (1-2 ngày)     Fix 6 bugs cứng
         │
Phase 1 (3-5 ngày)     Enrichment Pipeline + Data Expansion
         │              ⟵ BẮT ĐẦU VIẾT CHƯƠNG TỪ ĐÂY
Phase 2 (3-4 ngày)     Tách & Nâng cấp Audit System
         │
Phase 3 (2-3 ngày)     Style System + Dynamic Tone
         │
Phase 4 (2-3 ngày)     Canon Graph v2 + Butterfly Hardening
```

Mỗi phase độc lập deployable và testable. Tổng: ~12-17 ngày.

---

## 2. Phase 0 — Fix 6 Critical Bugs

**Mục tiêu:** Pipeline không còn lỗi logic. Mọi phase sau dựa trên nền này.

### 2.1 Bug 1: Butterfly Engine bị ngắt kết nối

**File:** `fanfic_pipeline/butterfly/divergence_ledger.py`
**Vấn đề:** `add_divergence()` chỉ append rồi `return []`, không gọi `propagator.propagate()` → ripples không bao giờ được sinh ra.

**Sửa:**
- Inject `Propagator`, `CausalGraph`, `ButterflyPolicy` vào `DivergenceLedger.__init__()`
- `add_divergence()` gọi `propagator.propagate()` → sinh ripples → append → return

```python
class DivergenceLedger:
    def __init__(self, propagator: Propagator, graph: CausalGraph, policy: ButterflyPolicy):
        self.propagator = propagator
        self.graph = graph
        self.policy = policy
        self.divergences: list[Divergence] = []
        self.ripples: list[Ripple] = []
        self.pod: Optional[POD] = None

    def add_divergence(self, div: Divergence) -> list[Ripple]:
        self.divergences.append(div)
        status = self.propagator.propagate(
            self.pod, self.divergences, self.graph, self.policy
        )
        new_ripples = self.propagator.ripples_from(status, self.graph, self.policy)
        self.ripples.extend(new_ripples)
        return new_ripples
```

### 2.2 Bug 2: `mark_satisfied()` logic sai

**File:** `fanfic_pipeline/butterfly/divergence_ledger.py`
**Vấn đề:** `if evidence not in evidence` luôn `False`.

**Sửa:** Đổi signature thêm `draft_text`, kiểm tra evidence là substring thật:

```python
def mark_satisfied(self, ripple_id: str, fic_chapter: int, 
                   evidence: str, draft_text: str) -> None:
    if evidence not in draft_text or len(evidence) < 5:
        raise ValueError("Evidence phải là substring thật của draft và ≥ 5 ký tự")
    # ... mark ripple as satisfied
```

### 2.3 Bug 3: Public facts bị chặn

**File:** `fanfic_pipeline/packages/canon/epistemic_ledger.py`
**Vấn đề:** `visible_to()` kiểm tra `known_by` trước `secrecy`, chặn public facts.

**Sửa:** Đảo thứ tự:

```python
def visible_to(self, actor: str, fact_id: str, canon_time: int) -> bool:
    f = self.facts.get(fact_id)
    if not f:
        return False
    if f.secrecy == "public":
        return canon_time >= f.since_chapter
    if f.secrecy == "forbidden":
        return False
    if actor not in f.known_by:
        return False
    return canon_time >= f.since_chapter
```

### 2.4 Bug 4: `_check_frozen_canon` bị shadow

**File:** `fanfic_pipeline/packages/auditor/matrix_33.py`
**Vấn đề:** Hàm được define ở dòng ~197 rồi bị define lại ở dòng ~288, shadow hoàn toàn bản đầu.

**Sửa:** Xóa bản define thứ 2 (dòng ~288), giữ bản đầu (dòng ~197) vì đầy đủ hơn.

### 2.5 Bug 5: 4 checker giả mạo

**File:** `fanfic_pipeline/packages/auditor/matrix_33.py`
**Vấn đề:** `ooc_fidelity`, `relationship_dynamics`, `pacing`, `canon_fidelity` luôn trả PASS.

**Sửa:** Đổi `status` trong `CHECKER_REGISTRY` từ `"implemented"` sang `"stub"`. Với logic fail-closed hiện có (`P0 UNKNOWN → REVISE`), pipeline sẽ REVISE thay vì PASS giả.

### 2.6 Bug 6: `hash_branch` không được evaluate

**File:** `fanfic_pipeline/packages/auditor/matrix_33.py`
**Vấn đề:** Có trong `CHECKER_REGISTRY` nhưng bị bỏ qua trong `ConsistencyVerificationStack.evaluate()`.

**Sửa:** Thêm `hash_branch` vào danh sách checker trong `evaluate()`.

### 2.7 Test Plan Phase 0

| Test ID | Nội dung | Kỳ vọng |
|---|---|---|
| P0-T1 | `DivergenceLedger.add_divergence()` với POD:001 | Sinh ≥ 1 ripple |
| P0-T2 | `mark_satisfied()` với evidence không có trong draft | Raise `ValueError` |
| P0-T3 | `EpistemicLedger.visible_to()` với public fact | Return `True` khi `canon_time ≥ since_chapter` |
| P0-T4 | AST scan: không checker nào `status="implemented"` mà thiếu đường FAIL | Pass |
| P0-T5 | Registry honesty: mọi fixture âm đều FAIL | Pass |
| P0-T6 | `hash_branch` xuất hiện trong `evaluate()` results | Pass |

---

## 3. Phase 1 — Enrichment Pipeline + Data Expansion

**Mục tiêu:** Chuyển pipeline từ "biết 5 nhân vật" sang "hiểu 1409 chương nguyên tác". Sau phase này bắt đầu viết chương.

### 3.1 Kiến trúc module mới

```
fanfic_pipeline/packages/enrichment/
├── __init__.py
├── batch_orchestrator.py      # Điều phối xử lý 1409 chương theo batch
├── structural_extractor.py    # Auto: entity, alias, realm, location, technique
├── semantic_extractor.py      # LLM: relationship, causal link, epistemic state
├── evidence_validator.py      # Verify record có substring thật từ nguyên tác
├── enrichment_store.py        # Lưu trữ persistent với provenance tracking
└── checkpoint.py              # Resume sau khi dừng giữa chừng
```

### 3.2 Batch Orchestrator

- Chia EPUB đã ingest thành cửa sổ 30 chương
- Xử lý tuần tự: Structural (auto) → Semantic (LLM) → Validate → Commit → Checkpoint
- Checkpoint sau mỗi window: `enrichment_progress.json` ghi window cuối hoàn thành
- Restart từ window tiếp theo nếu bị dừng giữa chừng
- Tổng thời gian ước tính: 4-8 giờ cho 1409 chương, chạy nền

### 3.3 Structural Extractor (Auto, 0 LLM token)

Chạy trên chunks trong CanonStore, dùng regex + pattern matching:

| Loại | Phương pháp | Output |
|---|---|---|
| Entity | `AliasNormalizer.entity_spans()` + expanded dictionary | Entity ID, first_seen_chapter, mention_count |
| Alias | Regex: `"A (tức B)"`, `"A，又名B"` | New alias → alias_registry |
| Realm | Keyword matching expanded realm list | Character X đạt Realm Y tại Ch Z |
| Location | NER pattern + known location dict | Location mention + chapter |
| Technique | Pattern: `"施展了X"`, `"运转X"`, `"一招X"` | Technique name + user + chapter |

Mỗi record kèm:
- `evidence_span`: substring thật từ chunk gốc
- `source_chapter`: chương nguồn
- `confidence_score`: 0.0-1.0

**Power Ladder expansion:** Quét 1409 chương tìm realm mentions → build danh sách đầy đủ bao gồm sub-tier (1-9 Trọng Thiên, Bán Bộ, Địa Tiên, Thiên Tiên...).

### 3.4 Semantic Extractor (LLM-based)

**Model:** Qwen 3.8 Max preferred, fallback GLM 5.2
**Input:** Tóm tắt 30 chương + entity list + structured JSON prompt

Trích xuất 5 loại:

```json
{
  "relationships": [
    {"from": "ENT:meng_qi", "to": "ENT:gu_xiaosang", 
     "type": "adversary_attraction", "since_chapter": 15,
     "evidence": "substring từ nguyên tác"}
  ],
  "causal_links": [
    {"cause_event": "EVT:0018:01", "effect_event": "EVT:0031:01",
     "necessity": "load_bearing", "evidence": "..."}
  ],
  "epistemic_states": [
    {"character": "ENT:meng_qi", "fact": "FACT:luc_dao_identity",
     "knows": false, "since_chapter": 1, "until_chapter": 847,
     "evidence": "..."}
  ],
  "mysteries": [
    {"id": "MYS:001", "question": "Ai là Chủ nhân Lục Đạo?",
     "answer_chapter": 1200, "evidence": "..."}
  ],
  "arc_summary": "Chương 1-30: Mạnh Kỳ gia nhập Lục Đạo..."
}
```

### 3.5 Evidence Validator

Hàng rào chống bịa đặt. Mọi record phải qua:

```python
def validate(record, source_chunks) -> tuple[bool, str]:
    if not record.evidence or len(record.evidence) < 10:
        return False, "evidence quá ngắn"
    normalized = normalize_fold(record.evidence)
    for chunk in source_chunks:
        if normalized in normalize_fold(chunk.text):
            return True, chunk.chunk_id
    return False, "evidence không tìm thấy trong nguyên tác"
```

Record không qua → `rejected_records.jsonl` kèm lý do, không commit.

### 3.6 Story Bible Auto-Generation

47 windows × `arc_summary` → LLM tổng hợp → Volume/Arc/Mini-Arc hierarchy:
- Volume boundaries (4-6 volumes)
- Arc boundaries (3-5 arcs per volume)
- Mini-arc boundaries (2-4 mini-arcs per arc)
- Mỗi arc có: title, objective, turning_points, antagonist, realm_milestone

Human review: Duyệt và điều chỉnh ranh giới, lưu `macro_bible_v2.py`.

### 3.7 Canon Exam thật

Thay mock hiện tại:
- Factual: Random entity/event → "Ai là sư phụ của X?"
- Temporal: Random timeline → "A trước hay sau B?"
- Rule: Random power_ladder → "Cảnh giới nào mới ngự không?"
- Epistemic: "Tại Ch 50, Mạnh Kỳ có biết thân phận Cố Tiểu Tang?"

LLM trả lời, so với ground truth trong enrichment store. Không tự điền đáp án.

### 3.8 Tích hợp

- `CanonStore.ingest_enrichment(records)`: nạp dữ liệu validated
- `ContextCompiler`: dùng enriched data thay hardcoded `knowledge.py`
- `HierarchicalPlanner`: load `macro_bible_v2` thay `macro_bible_v1`
- CLI: `fanfic_cli enrich --project X [--window 30] [--resume]`

### 3.9 Test Plan Phase 1

| Test ID | Nội dung | Kỳ vọng |
|---|---|---|
| P1-T1 | Structural extractor trên 30 chương đầu | Entity count ≥ 20 |
| P1-T2 | Evidence validator reject rate | < 25% |
| P1-T3 | Enrichment store persist + reload | Data intact |
| P1-T4 | Checkpoint resume: dừng window 3, restart | Tiếp từ window 4 |
| P1-T5 | Power ladder expansion | ≥ 15 realm tiers |
| P1-T6 | Canon exam (30 questions) | Không auto-pass |

---

## 4. Phase 2 — Tách & Nâng Cấp Audit System

**Mục tiêu:** Checker thật, modular, testable. Không còn checker giả.

### 4.1 Kiến trúc module mới

```
fanfic_pipeline/packages/auditor/
├── registry.py                    # CheckerRegistry
├── runner.py                      # AuditRunner (Fail-closed verdict + Actionable Revision Directives Generator)
├── receipt.py                     # AuditReceipt (chứa revision_directives)
├── checkers/
│   ├── base.py                    # BaseChecker ABC + CheckerResult(checker_id, status, severity, score, reason, actionable_fix)
│   ├── word_count.py              # Tier A — giữ nguyên
│   ├── alive_dead.py              # Tier A — giữ nguyên
│   ├── hash_branch.py             # Tier A — wire lại
│   ├── realm_strictness.py        # Tier A — nối enriched power_ladder
│   ├── resource_ledger.py         # Tier A — nối enriched data
│   ├── spatial_continuity.py      # Tier A — nối enriched locations
│   ├── timeline_consistency.py    # Tier A — giữ logic, bổ sung enriched timeline
│   ├── frozen_canon.py            # Tier A — load invariants từ enrichment
│   ├── canon_fidelity.py          # Tier B — VIẾT MỚI
│   ├── epistemic_leak.py          # Tier B — VIẾT MỚI
│   ├── ooc_fidelity.py            # Tier B — VIẾT MỚI (hybrid)
│   ├── relationship_dynamics.py   # Tier C — VIẾT MỚI (xét intimacy level)
│   ├── pacing.py                  # Tier C — VIẾT MỚI
│   ├── ai_pattern.py              # Tier C — Chặn degenerative repetition loop, BẢO TỒN các trope tiên hiệp/sảng văn đặc trưng
│   ├── pod_compatibility.py       # Tier B — tách từ cũ
│   ├── canon_orphan.py            # Tier B — tách, đã real

│   ├── butterfly_debt.py          # Tier B — tách, đã real
│   └── divergence_monotonicity.py # Tier B — tách, bỏ hardcode
└── fixtures/                      # Negative fixtures
```

### 4.2 BaseChecker Contract

```python
class BaseChecker(ABC):
    id: str
    tier: str         # "A" | "B" | "C"
    priority: str     # "P0" | "P1"

    @abstractmethod
    def check(self, ctx: AuditContext) -> CheckerResult:
        """Trả PASS, FAIL, REVISE, hoặc UNKNOWN. Không raise exception."""

    @abstractmethod
    def negative_fixtures(self) -> list[AuditContext]:
        """Mỗi fixture PHẢI trả FAIL khi chạy qua check()."""
```

Bắt buộc: Mọi checker `implemented` có ≥ 1 negative fixture. Test S1 (AST) + S2 (runtime) tự động.

### 4.3 AuditRunner

Thay thế `ConsistencyVerificationStack`:

```python
class AuditRunner:
    def evaluate(self, ctx: AuditContext) -> AuditReceipt:
        results = {c.id: c.check(ctx) for c in self.checkers}
        verdict = self._compute_verdict(results)
        return AuditReceipt(verdict=verdict, results=results,
                           draft_hash=ctx.draft_hash)
```

Verdict logic giữ nguyên fail-closed:
- `any(Tier A/B FAIL)` → FAIL
- `any(P0 UNKNOWN)` → REVISE
- `any(Tier C < threshold)` → REVISE
- else → PASS

### 4.4 Bốn checker mới

#### `ooc_fidelity.py` — Hybrid structural + LLM

**Bước 1 (Structural, 0 token):**
- Load CharacterVoice profile từ enrichment store
- Trích dòng thoại trong draft (regex `「...」`, `"..."`)
- Gán speaker, check xưng hô + từ cấm
- Vi phạm cứng → FAIL ngay

**Bước 2 (LLM, chỉ cho HITL chapters):**
- 3 dòng thoại đại diện + profile → LLM chấm 1-10
- < 6 → REVISE

#### `canon_fidelity.py` — Cross-reference enrichment store

- Map entity/event mentions trong draft về enrichment store qua alias_normalizer
- Check tồn tại tại canon_time, mô tả đúng, technique/realm phù hợp
- Không match → UNKNOWN; mâu thuẫn → FAIL

#### `relationship_dynamics.py` — Delta-based

- So relationship changes trong state_delta với relationship state hiện tại
- "Thù" → "yêu" trong 1 chương → REVISE
- Thay đổi mà không có scene interaction → REVISE

#### `pacing.py` — Metric-based

- Đo dialogue ratio, câu/đoạn length, scene transitions
- So baseline theo scene_type (combat vs emotional vs slice_of_life)
- Lệch quá xa → REVISE

### 4.5 Xóa `matrix_33.py` sau khi hoàn thành

Cập nhật import trong `engine.py` sang `AuditRunner`.

### 4.6 Test Plan Phase 2

| Test ID | Nội dung | Kỳ vọng |
|---|---|---|
| P2-T1 | AST scan mọi checker `implemented` có đường FAIL | Pass |
| P2-T2 | Mọi negative fixture → FAIL | Pass |
| P2-T3 | `len(registry.enabled) == docstring count` | Pass |
| P2-T4 | Integration: `write-next` end-to-end với audit mới | Verdict khớp |
| P2-T5 | Regression: toàn bộ test Phase 0 vẫn pass | Pass |

---

## 5. Phase 3 — Style System + Dynamic Tone Modulation

**Mục tiêu:** Văn phong biến thiên theo loại cảnh và giai đoạn truyện. Code-driven, 0 LLM token bổ sung.

### 5.1 Kiến trúc module mới

```
fanfic_pipeline/packages/style/
├── __init__.py
├── scene_classifier.py       # Phân loại cảnh → scene mode
├── tone_modifier.py          # Sinh dynamic style block
├── repetition_guard.py       # Bắt lặp cross-chapter
├── character_voice_arc.py    # Giọng nhân vật tiến hóa
└── metrics.py                # Đo nhịp điệu câu/đoạn/dialogue
```

### 5.2 Scene Classifier — 10 chế độ

| Mode | Đặc trưng |
|---|---|
| `combat` | Câu ngắn ≤ 15 từ, dialogue < 30%, động từ mạnh |
| `mystery` | Câu trung bình, quan sát, câu hỏi tu từ |
| `emotional` | Dialogue > 50%, câu dài, subtext |
| `cultivation` | Nội lực, ẩn dụ thiên nhiên, nhịp thiền |
| `political` | Đối thoại sắc bén, mưu tính |
| `slice_of_life` | Hài hước, ăn uống, bông đùa |
| `cosmology` | Triết lý, ngộ đạo, câu phức |
| `travel` | Tả cảnh, mở rộng thế giới |
| `flashback` | Hồi tưởng, so sánh xưa-nay |
| `climax` | Mix nhiều mode, tension cực đại |

Phân loại: Rule-based từ `beat.scene_type` trước, keyword fallback sau.

Mỗi mode có Style Metrics Baseline (đo từ nguyên tác qua enrichment):
```python
BASELINES = {
    "combat":    {"avg_sentence_len": 12, "dialogue_ratio": 0.20, "paragraph_len": 3},
    "emotional": {"avg_sentence_len": 22, "dialogue_ratio": 0.55, "paragraph_len": 5},
    # ...
}
```

### 5.3 Tone Modifier

Sinh ~100-150 từ style guidance, inject vào `SealedWriterPacket.style_contract`:

```python
def generate_tone_block(mode: str, chapter_num: int, char_states: dict) -> str:
    base = TONE_TEMPLATES[mode]
    # Điều chỉnh theo giai đoạn truyện
    if chapter_num < 50:
        base += "\nGiai đoạn mở đầu: nhịp khám phá, tò mò."
    elif chapter_num > 500:
        base += "\nGiai đoạn cao trào: giọng trầm lắng, sâu sắc."
    # Điều chỉnh theo tâm lý nhân vật hiện tại
    for char, state in char_states.items():
        if state.get("emotional_state"):
            base += f"\n{char}: {state['emotional_state']}"
    return base
```

### 5.4 Repetition Guard

Track 3-gram và 4-gram cross-chapter (window = 5 chương gần nhất):

```python
class RepetitionGuard:
    def __init__(self, window: int = 5):
        self.window = window
        self.ngram_index: dict[str, list[int]] = {}

    def ingest_chapter(self, chapter_num: int, text: str):
        for ngram in extract_ngrams(text, n=3):
            self.ngram_index.setdefault(ngram, []).append(chapter_num)

    def check_draft(self, chapter_num: int, draft: str) -> list[RepetitionWarning]:
        warnings = []
        for ngram in extract_ngrams(draft, n=4):
            recent = [ch for ch in self.ngram_index.get(ngram, [])
                      if chapter_num - ch <= self.window]
            if len(recent) >= 2:
                warnings.append(RepetitionWarning(phrase=ngram,
                    repeated_in_chapters=recent))
        return warnings
```

Tích hợp vào `pacing.py` checker: > 5 cụm lặp → REVISE.

### 5.5 Character Voice Arc

Voice Phases thay vì CharacterVoice cố định:

```python
class VoicePhase:
    chapter_range: tuple[int, int]
    personality_modifier: str
    dialogue_shift: str
    micro_behaviors_add: list[str]
    micro_behaviors_remove: list[str]
    trigger_event: str

class CharacterVoiceArc:
    character_id: str
    phases: list[VoicePhase]
```

Ví dụ Mạnh Kỳ:
- Phase 1 (Ch 1-50): Non nớt, trang bức che hoang mang
- Phase 2 (Ch 51-200): Tự tin, trêu đùa thoải mái
- Phase 3 (Ch 201-500): Trầm ổn, đao tâm vững
- Phase 4 (Ch 501+): Thâm trầm, mỗi câu có trọng lượng

Auto-generate phase boundaries từ enrichment (major character events = triggers).

### 5.6 Tích hợp

`SealedWriterPacket` thêm fields:
- `style_contract`: dynamic (thay chuỗi cứng)
- `repetition_avoid: list[str]`: cụm từ cần tránh
- `voice_phase: dict[str, str]`: character → current voice modifier

`ContextCompiler.compile_writer_packet()` gọi scene_classifier → tone_modifier → repetition_guard → voice_arc.

### 5.7 Test Plan Phase 3

| Test ID | Nội dung | Kỳ vọng |
|---|---|---|
| P3-T1 | Scene classifier trên 10 outline mẫu | Mode assignment hợp lý |
| P3-T2 | Tone modifier: cùng chapter, khác mode | Output khác biệt rõ rệt |
| P3-T3 | Repetition guard bắt cụm lặp 3+ lần | Cảnh báo chính xác |
| P3-T4 | Voice arc phase transition | Đúng chapter boundary |
| P3-T5 | Integration: 2 chương (combat + slice_of_life) | style_contract khác biệt |

---

## 6. Phase 4 — Canon Graph v2 + Butterfly Hardening

**Mục tiêu:** Nhân quả thật, scale 1000+ chương.

### 6.1 Canon Graph v2

Thay O(N²) bằng 2 nguồn cạnh + SQLite storage.

**File mới:** `fanfic_pipeline/packages/canon/canon_graph_v2.py`

#### Nguồn cạnh 1: LLM-verified causal links

Import trực tiếp `causal_links` từ Phase 1 semantic extractor. Cạnh chất lượng cao, có evidence.

#### Nguồn cạnh 2: Windowed proximity

Thay O(N²) bằng chapter bucket index (bucket = 10 chương):

```python
def build_proximity_edges(self, window: int = 10):
    buckets = self._group_by_bucket(window)
    for bucket_id, events in buckets.items():
        neighbors = events + buckets.get(bucket_id + 1, [])
        for a, b in combinations(neighbors, 2):
            if self._share_actor(a, b):
                self._add_edge(a, b, source_type="proximity")
```

Hiệu năng: ~20k phép tính thay vì 50M. Giảm ~2500x.

#### SQLite storage

```sql
CREATE TABLE events (
    id TEXT PRIMARY KEY, canon_chapter INTEGER, scope TEXT,
    necessity TEXT, actors TEXT, preconditions TEXT, evidence TEXT
);
CREATE INDEX idx_events_chapter ON events(canon_chapter);

CREATE TABLE edges (
    src TEXT, dst TEXT, necessity TEXT, strength REAL DEFAULT 0.8,
    source_type TEXT, PRIMARY KEY (src, dst)
);
CREATE INDEX idx_edges_src ON edges(src);
```

### 6.2 Butterfly Engine Hardening

#### 6.2.1 `violates_protected()` — Implement thật

```python
def violates_protected(self, event_id, protected_invariants) -> bool:
    event = self.graph.get_event(event_id)
    for inv_id in protected_invariants:
        inv = self.invariant_store.get(inv_id)
        if inv.protected_entities & set(event.actors):
            return True
        if inv.protected_facts & set(event.preconditions):
            return True
    return False
```

#### 6.2.2 Persistent Ripple IDs

Counter persistent trong `project_meta.json`:
```python
def next_ripple_id(self) -> str:
    self.ripple_counter += 1
    self._save_counter()
    return f"RIP:{self.ripple_counter:06d}"
```

#### 6.2.3 Counterfactual auto-refresh

```python
def on_new_divergence(self, div, propagator, graph, policy):
    seeds = graph.depends_on_fact(div.fact)
    delta = propagator.propagate_from(seeds, self.status)
    self.status = merge_worse(self.status, delta)
    self.divergence_count += 1
    if self.divergence_count % 25 == 0:
        self.status = propagator.propagate(...)  # full recompute
```

#### 6.2.4 `divergence_monotonicity` — Bỏ hardcode

Load `never_converge` từ `convergence.json`, check toàn bộ danh sách thay vì 1 fact.

#### 6.2.5 Nối Butterfly vào `write-next` end-to-end

```
write_next()
  ├── DivergenceLedger.ripples_due(ch)   → inject SealedWriterPacket
  ├── Counterfactual.cannot_happen()     → inject forbidden list
  ├── Writer viết draft
  ├── DivergenceExtractor.extract(draft) → phát hiện divergence mới
  ├── DivergenceLedger.add_divergence()  → propagate + sinh ripples
  ├── DivergenceLedger.mark_satisfied()  → đánh dấu ripples đã trả
  ├── AuditRunner.evaluate()             → butterfly_debt, canon_orphan
  └── Transaction.commit()               → ghi divergences + ripples + counterfactual
```

### 6.3 Fault Injection mở rộng

4 stage mới: `after_graph`, `after_divergences`, `after_ripples`, `after_counterfactual`
Nối với 5 stage hiện có. Tất cả 9 stage phải "NONE (atomic OK)".

### 6.4 Test Plan Phase 4

| Test ID | Nội dung | Kỳ vọng |
|---|---|---|
| P4-T1 | Build graph từ 10k events | < 30 giây |
| P4-T2 | `propagate()` trên 10k events | < 5 giây |
| P4-T3 | `depends_on_fact()` query | < 10ms |
| P4-T4 | 500 ripples đồng thời | `dedupe_and_cap` ≤ 40 active |
| P4-T5 | Incremental recompute 20x vs full | Trùng khớp |
| P4-T6 | POD:001 fixture (SPEC §B8) | Kết quả khớp worked example |
| P4-T7 | B-T5: POD incidental → 0 cannot_happen | Pass |
| P4-T8 | B-T6: POD load_bearing → ≥1 cannot_happen | Pass |
| P4-T9 | End-to-end 3 chương: ripples sinh → due → satisfied | Pass |
| P4-T10 | Fault injection 9 stage | Tất cả "NONE (atomic OK)" |

---

## 7. Phi Mục Tiêu (Không làm trong scope này)

- Universal support cho fandom khác (chỉ optimize 一世之尊)
- Web UI / dashboard
- EPUB/PDF export
- Fine-tune model riêng
- Đa ngữ output
- Tự động đánh giá chất lượng văn học (giữ mức checker + LLM critic hiện có)

---

## 8. Rủi Ro & Giảm Thiểu

| Rủi ro | Xác suất | Giảm thiểu |
|---|---|---|
| Enrichment tạo ra dữ liệu sai → viết sai canon | Cao | Evidence validator + reject rate monitor + Canon Exam gate |
| LLM viết lặp dù có Style System | Trung bình | Repetition Guard + expanding banned phrase list over time |
| Canon Graph vẫn chậm ở 20k+ events | Thấp | SQLite indexing + batch query + benchmark test P4-T1 |
| Phase chồng chéo gây regression | Trung bình | Mỗi phase có regression test chạy lại toàn bộ test trước |
| Story Bible auto-gen sai arc boundary | Cao | Human review bắt buộc trước khi commit macro_bible_v2 |

---

## 9. Thứ Tự Đọc Spec Khi Bắt Đầu Code

1. §2 (Phase 0) — sửa bug trước, nền móng cho mọi thứ
2. §3.3-3.5 (Structural + Semantic + Validator) — core enrichment
3. §3.6 (Story Bible) — chạy sau enrichment hoàn thành
4. §4.2-4.4 (BaseChecker + AuditRunner + 4 checker mới) — đọc cùng lúc
5. §5.2-5.5 (Scene Classifier → Tone → Repetition → Voice Arc) — đọc tuần tự
6. §6.1-6.2 (Graph v2 + Butterfly) — đọc cùng SPEC gốc §B3 và §B8
7. §6.3-6.4 (Fault injection + Test) — viết test trước code
