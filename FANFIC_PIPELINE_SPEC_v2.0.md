
---

# PHẦN B — BUTTERFLY EFFECT ENGINE
# "Hiệu ứng cánh bướm"

## B1. Mô hình khái niệm

### B1.1 Vì sao đây là bản chất của fanfic

Fanfic = canon + **một thay đổi** + **hệ quả của thay đổi đó**.

Bỏ số hạng thứ ba thì kết quả không phải fanfic mà là "canon viết lại bằng lời khác". Đây chính là điểm yếu lớn nhất của v1.1.3.1: hệ thống có `pod_compatibility` cho điểm cảm tính, nhưng **không có bất kỳ cơ chế nào biến một thay đổi thành hệ quả bắt buộc phải xuất hiện ở chương sau**. Nghĩa là AI có thể đổi một chi tiết ở chương 5 rồi hoàn toàn quên nó ở chương 6 — và không gì trong pipeline phát hiện được.

Ngược lại, nguy hiểm đối xứng cũng thật: nếu mọi thay đổi lan truyền không kiểm soát thì đến chương 30 thế giới không còn nhận ra được, và fanfic mất luôn cái mà người đọc tìm đến — cảm giác vẫn là thế giới đó. Engine này phải giải **cả hai** phía.

### B1.2 Sáu khái niệm

| Khái niệm | Định nghĩa | Vì sao cần |
|---|---|---|
| **POD** (Point of Divergence) | Điểm và nội dung thay đổi so với canon | Neo gốc cho mọi tính toán |
| **Divergence** | Một fact canon bị đổi/xoá/thêm | Đơn vị thay đổi có thể lần vết |
| **Ripple** | Hệ quả bắt buộc phải thể hiện, có deadline | Buộc thay đổi phải "trả nợ" |
| **Counterfactual status** | Trạng thái mỗi canon event sau POD | Biết còn được nhắc tới hay không |
| **Inertia** (quán tính) | Sức đề kháng của canon theo phạm vi | Chống lan truyền quá đà |
| **Convergence** | Canon tự kéo về đường cũ khi đủ xa POD | Giữ được "vẫn là thế giới đó" |

### B1.3 Bốn trạng thái của một canon event sau POD

```
intact         : preconditions còn đủ  -> vẫn xảy ra như canon
weakened       : precondition contingent bị mất -> xảy ra nhưng khác đi
altered        : xảy ra, nhưng actor/place/kết quả đổi
cannot_happen  : precondition load_bearing bị mất -> KHÔNG BAO GIỜ xảy ra
```

`cannot_happen` là trạng thái đáng giá nhất. Nó cho phép checker phát hiện lỗi kinh điển của fanfic AI: **nhắc tới một sự kiện canon như thể nó đã xảy ra, trong khi chính POD của truyện đã làm nó không thể xảy ra**. Con người viết fanfic cũng mắc lỗi này thường xuyên; AI mắc gần như chắc chắn nếu không có cơ chế.

---

## B2. Schema

### B2.1 POD — `butterfly/pod.json`

```json
{
  "id": "POD:001",
  "anchor_canon_chapter": 18,
  "statement": "Tại canon ch.18, Mạnh Kỳ tiết lộ thân phận Lục Đạo Luân Hồi cho Giang Chỉ Vi",
  "kind": "epistemic",
  "scope": "personal",
  "intensity": 0.7,
  "changed_facts": [
    {"op": "assert", "fact": "FACT:gcv_knows_luc_dao", "at_fic_chapter": 1},
    {"op": "retract", "fact": "FACT:gcv_ignorant_luc_dao", "at_fic_chapter": 1}
  ],
  "protected_invariants": ["INV:001", "INV:010"],
  "author_intent": "Đổi quan hệ Mạnh Kỳ - Giang Chỉ Vi, KHÔNG đổi cục diện Cửu Châu",
  "convergence_target": {"canon_chapter": 400, "mode": "soft"}
}
```

Ba trường thường bị bỏ quên nhưng quyết định chất lượng:

- **`protected_invariants`** — tác giả tuyên bố trước điều gì KHÔNG được lan tới. Không có nó thì propagator không biết đâu là giới hạn và sẽ phá luật thế giới.
- **`author_intent`** — dùng làm mốc cho `divergence_monotonicity` và cho reviewer người.
- **`convergence_target`** — "đến canon ch.400 thì cục diện lớn nên hội tụ lại". Đây là knob giữ cho fanfic không biến thành truyện khác hoàn toàn.

`kind ∈ {epistemic, action, survival, acquisition, relationship, timing, presence}`.
`scope ∈ {personal, local, faction, world}` (tăng dần độ nguy hiểm khi lan truyền).

### B2.2 Divergence — `butterfly/divergences.jsonl`

```json
{"id": "DIV:007", "pod": "POD:001", "origin_fic_chapter": 12,
 "op": "retract", "fact": "FACT:5c2ee901",
 "cause": "Mạnh Kỳ không nhận lệnh bài vì Giang Chỉ Vi đã can thiệp",
 "tier": 1, "scope": "personal",
 "registered_by": "auto_extract", "approved": true}
```

Divergence sinh từ 2 nguồn: (a) POD ban đầu, (b) **tự động trích từ draft mỗi chương** (mở rộng `StateExtractor` đã có, giữ nguyên rule evidence-substring đã cứu BUG-06).

`approved` cho chế độ HITL: divergence chưa duyệt thì write-next chương sau bị chặn — vì viết tiếp trên một thay đổi chưa được xác nhận là tích luỹ rủi ro.

### B2.3 Ripple — `butterfly/ripples.jsonl`

```json
{
  "id": "RIP:042",
  "from_divergence": "DIV:007",
  "tier": 1,
  "scope": "personal",
  "expected_manifestation": "Giang Chỉ Vi thay đổi cách đối xử với Mạnh Kỳ trước mặt người Tố Nữ Đạo",
  "affected_entities": ["ENT:char:giang_chi_vi", "ENT:org:to_nu_dao"],
  "due_fic_chapter_range": [12, 15],
  "status": "open",
  "satisfied_by": null,
  "priority": 0.82,
  "decay": 0.6
}
```

`status ∈ {open, due, satisfied, overdue, waived}`.

Hai điều làm ripple khác một "ghi chú TODO" bình thường:
1. **Có deadline cứng** (`due_fic_chapter_range`). Quá hạn ⇒ `overdue` ⇒ audit FAIL. Không có deadline thì hệ quả sẽ bị hoãn vô hạn — đúng cái bệnh của AI viết truyện dài.
2. **Được bơm vào packet** khi tới hạn (`ripples_due` ở §A6.2). Ripple không vào prompt thì writer không có cách nào biết để trả.

`waived` bắt buộc kèm `waive_reason` do người ghi. Máy không được tự tha nợ.

### B2.4 Counterfactual — `butterfly/counterfactual.json`

```json
{
  "computed_from": {"pod": "POD:001", "divergences_upto": "DIV:007", "graph_hash": "..."},
  "events": {
    "EVT:0031:01": {"status": "cannot_happen", "reason": "mất FACT:5c2ee901 (load_bearing)", "depth": 1},
    "EVT:0044:02": {"status": "altered", "reason": "actor đổi", "depth": 2},
    "EVT:0102:05": {"status": "weakened", "depth": 3, "damped": 0.22},
    "EVT:0300:01": {"status": "intact", "reason": "world scope + inertia cao"}
  },
  "stats": {"cannot_happen": 3, "altered": 11, "weakened": 24, "intact": 1188}
}
```

Trường `stats` là công cụ chẩn đoán quan trọng: nếu `cannot_happen` chiếm >5% tổng event thì propagator đang quá hung hăng; nếu = 0 sau một POD `load_bearing` thì propagator đang chết. Cả hai đều là bug và cả hai đều **âm thầm** nếu không có số này.

---

## B3. Thuật toán lan truyền — `butterfly/propagator.py` 🆕

### B3.1 Pseudocode

```python
INERTIA = {"personal": 0.15, "local": 0.35, "faction": 0.60, "world": 0.85}
NECESSITY_TRANSMIT = {"load_bearing": 1.0, "contingent": 0.5, "incidental": 0.0}

def propagate(pod, divergences, graph, policy):
    status = {}                      # event_id -> (status, depth, force)
    queue  = deque()

    # Bước 1: hạt giống — event nào phụ thuộc trực tiếp fact bị đổi
    for div in divergences:
        for ev in graph.depends_on_fact(div.fact):
            queue.append((ev, 1, div.intensity, div))

    while queue:
        ev, depth, force, src = queue.popleft()
        if depth > policy.max_depth:            # trần độ sâu (mặc định 5)
            continue

        # Bước 2: quán tính theo phạm vi — càng lớn càng khó đổi
        resist = INERTIA[ev.scope] * policy.inertia_gain
        effective = force * (1 - resist)
        if effective < policy.threshold:         # mặc định 0.12
            continue                             # canon giữ nguyên tại đây

        # Bước 3: quyết định trạng thái theo NECESSITY của precondition bị mất
        lost = [p for p in ev.preconditions if not holds_after(p, divergences)]
        if any(graph.necessity_of_precondition(ev, p) == "load_bearing" for p in lost):
            new_status = "cannot_happen"
        elif lost:
            new_status = "altered" if effective > 0.4 else "weakened"
        else:
            new_status = "intact"

        # Bước 4: bảo vệ bất biến do tác giả tuyên bố
        if violates_protected(ev, pod.protected_invariants):
            new_status = "intact"                # KHÔNG cho lan tới đây
            log_blocked(ev, "protected_invariant")

        status[ev.id] = merge_worse(status.get(ev.id), (new_status, depth, effective))

        # Bước 5: damping — lan tiếp với lực suy giảm
        if new_status != "intact":
            for edge in graph.out_edges(ev):
                transmit = NECESSITY_TRANSMIT[edge.dst.necessity]
                if transmit == 0.0:
                    continue                     # incidental không lan
                nxt = effective * edge.strength * transmit * policy.damping  # ~0.75
                queue.append((edge.dst, depth + 1, nxt, ev))

    return status
```

### B3.2 Bốn cơ chế kiểm soát, và lý do từng cái

| Cơ chế | Chống điều gì |
|---|---|
| `INERTIA[scope]` | POD cá nhân làm sụp cả cục diện Cửu Châu (vô lý và phá vỡ cảm giác thế giới) |
| `NECESSITY_TRANSMIT` | Chi tiết trang trí lan truyền như nhân quả thật (nổ combinatorial) |
| `damping` + `max_depth` | Vòng lặp lan vô hạn, mọi event thành broken |
| `protected_invariants` | Propagator phá đúng thứ tác giả muốn giữ |

Cả bốn phải có mặt đồng thời. Thiếu ba cái đầu ⇒ engine "đốt" cả canon. Thiếu cái cuối ⇒ engine đúng về logic nhưng sai về ý đồ nghệ thuật.

### B3.3 Sinh ripple từ kết quả lan truyền

```python
def ripples_from(status, graph, policy):
    out = []
    for ev_id, (st, depth, force) in status.items():
        if st == "intact":
            continue
        ev = graph.event(ev_id)
        out.append(Ripple(
            tier = min(depth, 3),
            scope = ev.scope,
            expected_manifestation = describe_consequence(ev, st),  # LLM diễn giải
            affected_entities = ev.actors,
            # Càng gần (tier thấp) càng phải trả sớm
            due_fic_chapter_range = due_window(depth, force, policy),
            priority = force * (1.0 if st == "cannot_happen" else 0.6),
            decay = policy.damping ** depth,
        ))
    return dedupe_and_cap(out, policy.max_open_ripples)   # mặc định 40
```

```python
def due_window(depth, force, policy):
    base = {1: (0, 3), 2: (2, 8), 3: (5, 20)}[min(depth, 3)]
    now = current_fic_chapter()
    return [now + base[0], now + base[1]]
```

Tier 1 phải trả trong 3 chương, tier 3 có thể đợi 20 chương. Đây là cách biến "hiệu ứng cánh bướm" từ ý tưởng thành **lịch trình có thể kiểm tra được**.

`dedupe_and_cap` với trần 40 ripple mở là biện pháp chống phình nợ ở chương 300+ — vấn đề đã nêu trong bảng rủi ro của PLAN.

---

## B4. Tính lại counterfactual tăng dần — `butterfly/counterfactual.py` 🆕

Tính lại toàn bộ mỗi chương là không cần thiết và tốn kém.

```python
def recompute(new_divergence):
    # Chỉ mở rộng từ vùng bị ảnh hưởng, không chạy lại toàn graph
    seeds = graph.depends_on_fact(new_divergence.fact)
    delta = propagate_from(seeds, existing_status)
    cache.merge(delta)                       # merge_worse: trạng thái xấu hơn thắng
    if cache.drift_since_full_recompute > 0.3 or fic_chapter % 25 == 0:
        cache = full_recompute()             # định kỳ tính lại toàn phần để chống lệch tích luỹ
    return cache
```

`merge_worse` (trạng thái xấu hơn luôn thắng) là quyết định fail-closed: nếu hai đường lan truyền cho kết quả khác nhau về cùng một event, lấy kết quả nghiêm khắc hơn. Nhầm về phía "sự kiện này không còn xảy ra" thì mất một chút nguyên liệu; nhầm về phía "vẫn xảy ra" thì sinh lỗi canon mà người đọc thấy ngay.

---

## B5. Ledger và nối với `NarrativeDebtLedger` đã có

Pipeline đã có `NarrativeDebtLedger` với `due_hooks`. Ripple **không tạo hệ thống nợ thứ hai** mà đăng ký vào đúng hệ thống đó:

```python
class DivergenceLedger:
    def register_pod(self, pod: POD) -> None
    def add_divergence(self, div: Divergence) -> list[Ripple]     # tự propagate + sinh ripple
    def ripples_due(self, fic_chapter: int) -> list[Ripple]       # -> vào packet §A6.2
    def mark_satisfied(self, ripple_id: str, fic_chapter: int, evidence: str) -> None
    def overdue(self, fic_chapter: int) -> list[Ripple]           # -> checker butterfly_debt
    def waive(self, ripple_id: str, reason: str, by: str) -> None  # chỉ người
    def to_narrative_debt(self) -> list[DebtItem]                 # nối vào ledger cũ
```

`mark_satisfied` bắt buộc có `evidence` là **substring thật của draft** — cùng một nguyên tắc §0.3. Không có nó thì AI sẽ tự tuyên bố "đã trả nợ" mà không viết gì cả, và đây là dạng lỗi rất khó phát hiện bằng đọc thủ công.

---

## B6. Chính sách hội tụ — `butterfly/convergence.json`

```json
{
  "butterfly_gain": 1.0,
  "inertia_gain": 1.0,
  "damping": 0.75,
  "max_depth": 5,
  "threshold": 0.12,
  "max_open_ripples": 40,
  "convergence": {
    "mode": "soft",
    "start_canon_chapter": 400,
    "pull_strength": 0.3,
    "never_converge": ["FACT:gcv_knows_luc_dao"]
  }
}
```

Ba chế độ hội tụ, chọn theo ý đồ tác giả:

| Mode | Hành vi | Dùng khi |
|---|---|---|
| `none` | Không kéo về canon; lệch mãi | AU hoàn toàn |
| `soft` | Cục diện lớn (scope world/faction) dần trở lại canon; chuyện cá nhân giữ lệch | **Mặc định cho fanfic** |
| `hard` | Mọi thứ trừ `never_converge` trở lại canon | Fanfic "vòng lặp thời gian", one-shot |

`never_converge` là danh sách fact **không bao giờ được kéo về canon** — chính là lõi của fanfic. Nếu cái thay đổi trung tâm bị hội tụ mất, truyện mất lý do tồn tại.

---

## B7. Bốn checker của Phần B

### B7.1 `pod_compatibility` (viết lại thật)

```
ĐẦU VÀO: draft, pod, counterfactual, divergence_ledger
QUY TẮC:
  - Draft trái POD (ví dụ POD nói Giang Chỉ Vi ĐÃ biết, draft viết cô ta không biết) -> FAIL
  - Draft phá protected_invariants -> FAIL
  - Draft mở rộng POD sang scope lớn hơn author_intent mà không đăng ký divergence -> REVISE
  - Không phát hiện được liên hệ nào với POD -> UNKNOWN (KHÔNG phải PASS)
```

### B7.2 `canon_orphan` 🆕 — checker giá trị nhất

```
QUY TẮC:
  1. Trích mọi tham chiếu sự kiện canon trong draft (span-bound).
  2. Map về event_id qua canon_graph + alias_map.
  3. Nếu event có status == "cannot_happen" và draft nhắc như ĐÃ xảy ra -> FAIL
  4. Nếu status == "altered"/"weakened" mà draft mô tả đúng như canon gốc -> REVISE
  5. Không map được -> UNKNOWN
```

Đây là checker duy nhất bắt được lỗi "AI dùng ký ức canon để viết một thế giới mà canon đó đã không còn đúng" — lỗi phổ biến nhất và khó thấy nhất của fanfic AI, vì từng câu đọc riêng đều đúng.

### B7.3 `butterfly_debt` 🆕

```
QUY TẮC:
  - Có ripple overdue -> FAIL   ("đổi rồi quên" — bệnh chính của AI viết dài)
  - Có ripple due trong chương này mà draft không thể hiện -> REVISE
  - Số ripple mở > max_open_ripples -> REVISE (nợ phình)
  - Ripple tier 1 tồn tại >5 chương chưa trả -> FAIL
```

### B7.4 `divergence_monotonicity` 🆕

```
QUY TẮC:
  - Fact trong never_converge bị âm thầm trả về giá trị canon -> FAIL
  - Divergence đã đăng ký bị đảo ngược không có sự kiện giải thích -> FAIL
  - Độ lệch canon giảm quá nhanh (> pull_strength cho phép) -> REVISE
```

Checkers này chống "trôi ngược": qua vài chục chương, AI có xu hướng quên POD và viết dần trở lại canon vì canon là thứ nó thấy nhiều nhất trong retrieval. Không có checker này thì đến chương 50 fanfic tự biến thành canon kể lại.

---

## B8. Ví dụ chạy đầy đủ (worked example)

Để spec không chỉ là khái niệm, đây là một lượt hoàn chỉnh.

### Thiết lập

```
POD:001  anchor=canon ch.18, kind=epistemic, scope=personal, intensity=0.7
  "Mạnh Kỳ tiết lộ thân phận Lục Đạo cho Giang Chỉ Vi"
  protected_invariants: [INV:001 (luật Khai Khiếu), INV:010 (địa lý Cửu Châu)]
  author_intent: "đổi quan hệ 2 người, KHÔNG đổi cục diện Cửu Châu"
  convergence: soft, start=400, never_converge=[FACT:gcv_knows_luc_dao]
```

### Bước 1 — Divergence gốc

```
DIV:001  assert  FACT:gcv_knows_luc_dao   (tier 0)
DIV:002  retract FACT:gcv_ignorant_luc_dao (tier 0)
```

### Bước 2 — Lan truyền

```
graph.depends_on_fact(FACT:gcv_ignorant_luc_dao) -> 4 event

depth 1:
  EVT:0031:01 "Giang Chỉ Vi tố giác người lạ mặt cho Tố Nữ Đạo"
     precondition mất: FACT:gcv_ignorant_luc_dao (load_bearing)
     scope=local, resist=0.35, effective=0.7*0.65=0.46
     => cannot_happen                         [biết rồi thì không tố giác nữa]

  EVT:0028:02 "Mạnh Kỳ phải che giấu trước Giang Chỉ Vi"
     => cannot_happen                          [không còn gì để che]

depth 2 (force 0.46*0.9*1.0*0.75 = 0.31):
  EVT:0044:02 "Tố Nữ Đạo truy sát người lạ mặt"
     precondition mất: hệ quả của EVT:0031:01 (contingent)
     scope=faction, resist=0.60, effective=0.31*0.40=0.12
     => weakened (sát ngưỡng 0.12)             [vẫn truy sát, nhưng vì lý do khác]

depth 3 (force 0.12*0.75 = 0.09 < threshold):
  DỪNG. Cục diện Cửu Châu không bị ảnh hưởng.  ✅ khớp author_intent

Bị chặn bởi protected_invariants:
  EVT:0120:04 (liên quan INV:010 địa lý) -> giữ intact, log "protected_invariant"
```

### Bước 3 — Ripple sinh ra

```
RIP:001 tier1 personal due[1,4]   "Giang Chỉ Vi thay đổi cách gọi/đối xử với Mạnh Kỳ"
RIP:002 tier1 local    due[1,4]   "Tố Nữ Đạo KHÔNG nhận được tin tố giác -> phản ứng chậm"
RIP:003 tier2 personal due[3,9]   "Giang Chỉ Vi phải chọn: giữ bí mật hay báo tông môn"
RIP:004 tier2 faction  due[3,9]   "Truy sát của Tố Nữ Đạo đổi động cơ"
```

### Bước 4 — Đưa vào packet chương fanfic 1

```json
{
  "counterfactual": {"cannot_happen": ["EVT:0031:01", "EVT:0028:02"],
                     "weakened": ["EVT:0044:02"]},
  "ripples_due": ["RIP:001", "RIP:002"],
  "forbidden": [
    "KHÔNG viết Giang Chỉ Vi tố giác Mạnh Kỳ (EVT:0031:01 không còn xảy ra)",
    "KHÔNG viết Mạnh Kỳ che giấu thân phận với Giang Chỉ Vi",
    "KHÔNG cho Mạnh Kỳ bay/ngự không (Khai Khiếu, INV:001)"
  ]
}
```

### Bước 5 — Audit chương vừa viết

| Checker | Tình huống giả định | Kết quả |
|---|---|---|
| `canon_orphan` | Draft viết "sau khi Giang Chỉ Vi tố giác chàng..." | **FAIL** — nhắc EVT:0031:01 (cannot_happen) như đã xảy ra |
| `butterfly_debt` | Draft không thể hiện RIP:001, RIP:002 | **REVISE** — 2 ripple đến hạn chưa trả |
| `pod_compatibility` | Draft viết Giang Chỉ Vi vẫn không biết gì | **FAIL** — trái POD |
| `frozen_canon` | Draft cho Mạnh Kỳ bay lượn | **FAIL** — INV:001 |
| `divergence_monotonicity` | Chương 30 viết Giang Chỉ Vi "chưa từng biết" | **FAIL** — never_converge bị đảo |

Đây chính là năm loại lỗi mà v1.1.3.1 **không bắt được một cái nào**. Ví dụ này đồng thời là bộ regression fixture đầu tiên cho P2 (xem §8.3).

---

## B9. API Phần B

```python
class Propagator:
    def propagate(self, pod, divergences, graph, policy) -> dict[str, EventStatus]
    def ripples_from(self, status, graph, policy) -> list[Ripple]

class Counterfactual:
    def status_of(self, event_id: str) -> EventStatus
    def cannot_happen(self) -> list[str]
    def recompute(self, new_divergence) -> None
    def stats(self) -> dict

class ConvergencePolicy:
    def load(self, path) -> Policy
    def pull_toward_canon(self, fic_chapter, canon_time) -> float
    def is_protected(self, fact_id) -> bool
```

---

# 4. TÍCH HỢP VÀO VÒNG VIẾT CHƯƠNG

## 4.1 `write-next` v2 — trình tự đầy đủ

```python
def write_next(proj, instruction, mode):
    # --- CỔNG CHẶN (trước khi tốn token) ---
    require_canon_ingested(proj)                      # ✅ đã có v1.1.3.1
    CanonExam(proj).gate()                            # 🆕 A7.3
    require_no_overdue_ripples(proj)                  # 🆕 B7.3
    if mode == "hitl": require_approved_divergences(proj)   # 🆕 B2.2

    n = state.current_chapter + 1
    canon_time = plan.canon_time_for(n)
    pov = plan.pov_for(n)

    # --- XÂY PACKET v2 ---
    retrieved = retrieve_canon(instruction, canon_time, pov)     # 🆕 A6.1
    cf        = counterfactual.snapshot()                        # 🆕 B4
    ripples   = ledger.ripples_due(n)                            # 🆕 B5
    packet    = compile_writer_packet_v2(retrieved, cf, ripples, plan)  # ⏳

    # --- VIẾT ---
    draft = writer.write_draft(outline, sealed_packet=packet)     # ✅ đã bind đúng

    # --- TRÍCH XUẤT ---
    delta      = state_extractor.extract(draft)                   # ✅ 5/5 test
    new_divs   = divergence_extractor.extract(draft, packet)      # 🆕
    new_ripples= ledger.add_divergence_batch(new_divs)            # 🆕 tự propagate

    # --- AUDIT v2 ---
    verdict = matrix_v2.evaluate(draft, delta, packet, cf, ledger,
                                risk_level=RiskProfiler.compute_risk(...))  # ✅
    if verdict != "PASS": return revise_loop(...)

    # --- COMMIT ATOMIC (một transaction cho TẤT CẢ) ---
    with tx.begin(n) as t:                                        # ✅ atomic 5/5
        t.write_chapter(draft); t.write_state(delta)
        t.write_graph_updates(...)        # 🆕 epistemic.learn(...)
        t.write_divergences(new_divs)     # 🆕
        t.write_ripples(new_ripples)      # 🆕
        t.mark_ripples_satisfied(...)     # 🆕
        t.write_meta(); t.write_memory()
```

## 4.2 Ba cổng chặn trước khi tốn token

Thứ tự có chủ ý: chặn **trước** khi gọi LLM. Viết một chương rồi mới phát hiện có ripple quá hạn là đã đốt 30k token và làm bẩn state.

## 4.3 Yêu cầu atomicity mở rộng

Tất cả file `canon/*` và `butterfly/*` bị ghi trong commit **phải nằm trong cùng transaction** với chapter + state. Mở rộng `FANFIC_FAULT_INJECT` thêm các stage:

```
after_graph | after_divergences | after_ripples | after_counterfactual
```

Mỗi stage phải đạt "NONE (atomic OK)" như 5 stage hiện có. Lý do bắt buộc: nếu ripple được ghi mà chapter bị rollback, hệ thống sẽ đòi nợ cho một chương không tồn tại — và không có cách nào tự phát hiện.

---

# 5. AUDIT REGISTRY v2

| # | checker_id | Tier | Nhóm | Trạng thái v2 | Fail policy |
|---|---|---|---|---|---|
| 1 | `word_count` | A | form | ✅ giữ | FAIL blocks |
| 2 | `realm_strictness` | A | canon rule | ⏳ nối `power_ladder` | FAIL blocks |
| 3 | `alive_dead` | A | canon fact | ⏳ nối `status_timeline` | FAIL blocks |
| 4 | `hash_branch` | A | integrity | ✅ giữ | FAIL blocks |
| 5 | `resource_ledger` | A | state | ⏳ implement thật | FAIL blocks |
| 6 | `timeline_consistency` | A | **temporal** | 🔴 **viết thật (§6.1)** | FAIL blocks |
| 7 | `frozen_canon` | A | **canon rule** | 🔴 **viết thật (§6.2)** | FAIL blocks |
| 8 | `spatial_continuity` | A | canon fact | ⏳ nối graph place | UNKNOWN→REVISE |
| 9 | `canon_fidelity` | A | **canon** | 🆕 §A8 | FAIL blocks |
| 10 | `epistemic_leak` | A | **canon** | 🆕 (ai biết gì) | FAIL blocks |
| 11 | `pod_compatibility` | B | **butterfly** | 🆕 §B7.1 | FAIL blocks |
| 12 | `canon_orphan` | B | **butterfly** | 🆕 §B7.2 | FAIL blocks |
| 13 | `butterfly_debt` | B | **butterfly** | 🆕 §B7.3 | FAIL blocks |
| 14 | `divergence_monotonicity` | B | **butterfly** | 🆕 §B7.4 | FAIL blocks |
| 15 | `ooc_fidelity` | C | voice | ✅ giữ | REVISE |
| 16 | `relationship_dynamics` | C | voice | ✅ giữ | REVISE |
| 17 | `pacing` | C | craft | ✅ giữ | REVISE |
| 18 | `ai_pattern` | C | craft | ✅ giữ | REVISE |

**18 checker, 0 stub được gắn nhãn implemented.** Tên module đổi thành `consistency_stack.py` (bỏ tên "matrix_33" — con số 33 không bao giờ đúng và đã gây nhầm lẫn trong audit của bạn).

Quy tắc verdict giữ nguyên logic fail-closed đã nghiệm thu của v1.1.3:

```
any(Tier A/B FAIL)          -> FAIL   (chặn commit)
any(P0 UNKNOWN)             -> REVISE (không bao giờ PASS)
any(Tier C dưới ngưỡng)     -> REVISE
else                        -> PASS
```

---

# 6. SPEC HAI CHECKER ĐANG HỒI QUY

Phần này đặc tả chi tiết vì đây là hồi quy an toàn đã đo được ở v1.1.3.1: cả hai đang gắn nhãn `implemented` nhưng trả PASS trên mọi đầu vào, kể cả văn bản rỗng.

## 6.1 `timeline_consistency` — viết thật

```python
def check_timeline(draft, packet, state, graph) -> CheckerResult:
    # 0. FAIL-CLOSED trước tiên
    if not draft or len(draft) < 50:
        return UNKNOWN("draft quá ngắn để kiểm tra")     # KHÔNG PASS như hiện nay

    issues = []

    # 1. Trích mọi biểu thức thời gian (regex + normalize không dấu)
    #    "ba năm sau", "hôm qua", "nửa canh giờ trước", "mùa đông năm ngoái"
    marks = extract_time_marks(draft)

    # 2. Mâu thuẫn nội bộ chương: mốc lùi sau mốc tiến trong cùng dòng thời gian
    for a, b in consecutive_pairs(marks):
        if a.direction == "forward" and b.direction == "backward" \
           and not in_flashback_block(b):
            issues.append(f"Mốc lùi '{b.text}' sau mốc tiến '{a.text}' ngoài hồi tưởng")

    # 3. So với story_day của chương trước
    if state.prev_story_day and marks:
        elapsed = infer_elapsed(marks)
        if elapsed < 0:
            issues.append(f"Thời gian đi lùi so với chương trước ({elapsed})")
        if elapsed > MAX_JUMP_PER_CHAPTER and "time_skip" not in outline.tags:
            issues.append(f"Nhảy {elapsed} ngày mà outline không khai báo time_skip")

    # 4. So với canon_time: draft nhắc event canon có canon_chapter > canon_time_max
    for ref in extract_canon_event_refs(draft, graph):
        if ref.canon_chapter > packet.canon_time_max:
            issues.append(f"Nhắc {ref.id} (canon ch.{ref.canon_chapter}) "
                          f"vượt canon_time_max={packet.canon_time_max}")   # spoiler

    # 5. Tuổi/tu vi tăng phi lý so với thời gian trôi
    for c, realm_change in state.realm_changes.items():
        if not power_ladder.plausible(realm_change, elapsed):
            issues.append(f"{c}: {realm_change} trong {elapsed} ngày — phi lý")

    if issues:  return FAIL(issues)                       # PHẢI có đường FAIL
    if not marks: return UNKNOWN("không tìm thấy mốc thời gian")
    return PASS("timeline nhất quán")
```

Fixture âm bắt buộc (6 ca, mỗi ca phải FAIL):
1. "Ba năm sau... nhưng hôm qua chàng mới vào Lục Đạo"
2. story_day chương này < chương trước
3. Nhảy 10 năm không khai báo time_skip
4. Nhắc event canon ch.900 khi canon_time_max=63
5. Khai Khiếu → Nguyên Thần trong 3 ngày
6. Draft rỗng / <50 ký tự → UNKNOWN (không PASS)

## 6.2 `frozen_canon` — viết thật

```python
def check_frozen_canon(draft, state, invariants, ladder, ledger) -> CheckerResult:
    if not draft:  return UNKNOWN("draft rỗng")           # KHÔNG PASS

    low = normalize_fold(draft)          # bỏ dấu + lowercase (A2.1)
    issues = []

    for inv in invariants:               # DỮ LIỆU, không hard-code
        if inv.kind == "power_rule":
            realm = state.realm_of(inv.detect["subject"] or pov)
            if ladder.rank_of(realm) <= ladder.rank_of(inv.detect["realm"]):
                for act in inv.detect["forbidden_acts"]:
                    if normalize_fold(act) in low:        # khớp cả không dấu
                        issues.append((inv, act, span_of(act, draft)))

        elif inv.kind == "identity_secret":
            if reveals_fact(draft, inv.detect["fact"]):
                if not ledger.has_approved_divergence(inv.detect["fact"]):
                    issues.append((inv, "tiết lộ không đăng ký", ...))

        elif inv.kind == "world_structure":
            if contradicts_graph(draft, inv, graph):
                issues.append((inv, "trái cấu trúc thế giới", ...))

    hard = [i for i in issues if i[0].severity == "hard"]
    if hard:   return FAIL(hard)
    if issues: return REVISE(issues)
    if not invariants: return UNKNOWN("chưa có frozen_invariants — chạy canon build-graph")
    return PASS(f"kiểm {len(invariants)} bất biến, không vi phạm")
```

Ba điểm sửa so với bản hiện tại:
1. Duyệt **toàn bộ** invariants, không phải `[:5]` như code hiện tại.
2. Khớp trên chuỗi đã fold dấu ⇒ bắt được cả "bay luon" không dấu (bản hiện tại trượt).
3. Không có invariants ⇒ UNKNOWN, không PASS (bản hiện tại PASS score 9 khi danh sách rỗng — nghĩa là project chưa build graph thì checker này luôn xanh).

---

# 7. CLI v2

```bash
# Canon Mastery
fanfic_cli canon build-aliases  --project X
fanfic_cli canon build-graph    --project X --zone hot --pod-anchor 18
fanfic_cli canon stats          --project X
fanfic_cli canon rejected       --project X --top 20      # xem vì sao bị loại
fanfic_cli canon-exam           --project X [--n 300] [--holdout]
fanfic_cli canon ask            --project X --q "..." --canon-time 63 --pov manh_ky

# Butterfly
fanfic_cli pod set              --project X --file pod.json
fanfic_cli pod show             --project X
fanfic_cli butterfly propagate  --project X [--dry-run]
fanfic_cli butterfly status      --project X    # counterfactual stats + ripple mở
fanfic_cli ripple list          --project X [--due] [--overdue]
fanfic_cli ripple waive         --project X --id RIP:042 --reason "..."

# Viết (mở rộng lệnh đã có)
fanfic_cli write-next --project X --require-canon --require-exam --require-no-overdue
```

`--dry-run` cho `propagate` là bắt buộc: phải xem được POD sẽ phá những gì **trước khi** ghi vào ledger.

---

# 8. NGHIỆM THU

## 8.1 Test bất biến cấu trúc (chạy trong CI)

| ID | Nội dung | Kỳ vọng |
|---|---|---|
| S1 | Mọi checker `implemented` có ≥1 đường trả FAIL (phân tích AST) | Pass |
| S2 | Mọi checker `implemented` FAIL trên fixture âm của chính nó | Pass |
| S3 | Mọi node/edge/fact trong graph có evidence là substring thật | 100% |
| S4 | Mọi ripple có `due_fic_chapter_range` khác None | 100% |
| S5 | Mọi ID ổn định qua 2 lần build liên tiếp | 100% |
| S6 | `len(REGISTRY) == số dòng trong docstring` | Pass |

S1 và S2 là hàng rào trực tiếp chống lại loại lỗi đã xảy ra hai lần trong dự án này.

## 8.2 Test Phần A

| ID | Nội dung | Kỳ vọng |
|---|---|---|
| A-T1 | Truy vấn không dấu vs có dấu | Chênh ≤10% về số hit và độ dài evidence |
| A-T2 | Truy vấn CJK `孟奇` | Trả cả chunk tiếng Việt |
| A-T3 | `retrieve_canon(canon_time_max=63)` | 0 kết quả có canon_chapter > 63 |
| A-T4 | `visible_to(giang_chi_vi, FACT:luc_dao, 17)` | False (trước POD) |
| A-T5 | Bơm 10 event bịa (evidence sai) vào extractor | Bị loại 10/10 |
| A-T6 | `canon-exam` toàn phần | ≥85% / temporal ≥80% / rule ≥90% |
| A-T7 | Sửa graph rồi gọi `write-next` | Bị chặn vì exam stale |

## 8.3 Test Phần B (butterfly regression suite)

Dùng đúng POD:001 ở §B8 làm fixture cố định.

| ID | Nội dung | Kỳ vọng |
|---|---|---|
| B-T1 | `propagate(POD:001)` | `cannot_happen` ⊇ {EVT:0031:01, EVT:0028:02} |
| B-T2 | Số ripple sinh ra | ≥3, mỗi cái có deadline |
| B-T3 | Event scope=world ở canon ch.300+ | `intact` (quán tính hoạt động) |
| B-T4 | Event thuộc `protected_invariants` | `intact` + log `protected_invariant` |
| B-T5 | POD `incidental` thuần | 0 `cannot_happen` (không lan quá đà) |
| B-T6 | POD `load_bearing` | ≥1 `cannot_happen` (không chết máy) |
| B-T7 | Draft nhắc EVT:0031:01 như đã xảy ra | `canon_orphan` = FAIL |
| B-T8 | Ripple tier1 quá hạn 6 chương | `butterfly_debt` = FAIL |
| B-T9 | Chương 30 đảo `never_converge` fact | `divergence_monotonicity` = FAIL |
| B-T10 | `stats.cannot_happen / total` | Trong khoảng (0, 5%] |
| B-T11 | Recompute tăng dần 20 lần vs full recompute | Kết quả trùng khớp |

B-T5 và B-T6 là một cặp đối xứng có chủ ý: một cái bắt engine quá hung hăng, một cái bắt engine đã chết. Chỉ có một trong hai thì bug còn lại sẽ đi qua mà không ai thấy.

## 8.4 Test atomicity mở rộng

```bash
for stage in after_state after_workspace after_meta after_memory after_state_commit \
             after_graph after_divergences after_ripples after_counterfactual; do
    FANFIC_FAULT_INJECT=$stage python3 -m fanfic_pipeline.fanfic_cli write-next --project t
    # so hash toàn thư mục trước/sau -> phải "NONE (atomic OK)"
done
```

Năm stage đầu đã đạt ở v1.1.3.1. Bốn stage mới phải đạt cùng chuẩn.

## 8.5 Test đầu-cuối cho mốc M1

```
1. init --project fic1 --mode hitl
2. ingest --epub Q565.epub                      -> 1409 sections / 4355 chunks
3. canon build-aliases                          -> alias_map có ≥200 entity
4. canon build-graph --zone hot --pod-anchor 18  -> reject_rate < 25%
5. canon-exam                                   -> ≥85%, temporal ≥80%, rule ≥90%
6. pod set --file pod.json                      -> POD:001
7. butterfly propagate --dry-run                -> khớp §B8, 0 vi phạm protected
8. write-next  ×10 (HITL)                       -> 0 lỗi canon do người soát tìm ra
9. ripple list --overdue                        -> RỖNG
10. butterfly status                            -> cannot_happen ≤5%, ripple mở ≤40
```

Bước 8 và 9 là tiêu chí quyết định. Bước 9 rỗng nghĩa là mọi thay đổi đã được trả giá — tức là hiệu ứng cánh bướm thực sự hoạt động chứ không chỉ tồn tại trong file JSON.

---

# 9. PHI MỤC TIÊU (bản này không làm)

- Xuất bản: EPUB/PDF/audiobook, dàn trang, bìa
- Web UI / dashboard trực quan (CLI + file JSON là đủ cho M1–M2)
- Đa fandom (schema thiết kế sẵn để mở rộng, nhưng chỉ seed Nhất Thế Chi Tôn)
- Dịch đa ngữ đầu ra
- Fine-tune model riêng (dùng model qua router hiện có)
- Đánh giá chất lượng văn học tự động (giữ ở mức `ooc_fidelity` + `ai_pattern` hiện tại)

---

# 10. THỨ TỰ ĐỌC SPEC KHI BẮT ĐẦU CODE

1. §0 — quy ước, đặc biệt §0.3 (evidence binding) và §0.4 (trung thực nhãn)
2. §6 — hai checker hồi quy, làm trước để hàng rào an toàn hoạt động
3. §A2 — alias normalizer, vì mọi thứ sau phụ thuộc
4. §A4 — schema, chốt trước khi đốt token trích xuất
5. §A7 — canon exam, dựng sớm để có thước đo ngay từ đầu
6. §B2 → §B3 → §B8 — đọc ví dụ §B8 song song với thuật toán §B3
7. §4 — tích hợp
8. §8 — nghiệm thu, viết test trước khi viết code từng phần
