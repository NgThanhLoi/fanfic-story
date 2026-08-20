# KẾ HOẠCH BUILD — Fanfic Pipeline v2.0
## "Đủ để viết fanfic" (chưa bao gồm xuất bản)

- **Fandom mục tiêu:** Nhất Thế Chi Tôn (一世之尊) — canon 1.409 chương / 4.355 chunk đã ingest
- **Ngôn ngữ đầu ra:** Tiếng Việt
- **Baseline:** v1.1.3.1 (đã nghiệm thu: transaction atomic 5/5, rollback 100%, extractor 5/5, sealed packet OK, `--require-canon` OK)
- **Ngoài phạm vi bản này:** xuất bản (EPUB/PDF/audio), web UI, đa fandom, thương mại hoá

---

## 0. Luận điểm trung tâm của kế hoạch

Hai bản review vừa rồi cho thấy một điều: **hạ tầng đã vững hơn phần mềm nội dung**. Transaction, rollback, staging, fault-injection của pipeline này tốt hơn hầu hết repo cùng loại. Nhưng viết fanfic hay/đúng lại **không phụ thuộc vào hạ tầng** — nó phụ thuộc vào hai năng lực mà pipeline hiện **chưa có ở mức dùng được**:

| Năng lực | Câu hỏi nó trả lời | Hiện trạng v1.1.3.1 |
|---|---|---|
| **Hiểu, nắm rõ nguyên tác** | "Trong canon, chuyện gì đã xảy ra, ai biết gì, luật thế giới ra sao?" | Chỉ có RAG chunk thô. Không có sự kiện, không có quan hệ nhân quả, không có thang cảnh giới máy đọc được, không có bằng chứng nào cho thấy hệ thống *đã hiểu* |
| **Hiệu ứng cánh bướm** | "Sau khi tôi đổi 1 chi tiết, những gì trong canon còn đúng, những gì sụp đổ, hệ quả nào phải xuất hiện ở chương nào?" | Chỉ có 1 checker tên `pod_compatibility` chấm điểm cảm tính. Không có POD dữ liệu hoá, không có lan truyền, không có sổ nợ hệ quả |

Không có 2 tầng này thì kết quả tất yếu là: **fanfic đúng văn phong nhưng sai canon, và mọi thay đổi đều không có hệ quả** — tức là fanfic chết. Vì vậy toàn bộ khối lượng công việc chính của v2.0 nằm ở P1 và P2.

RAG chunk (v1.1.3) là **điều kiện cần, không phải điều kiện đủ**. Chunk cho biết "đoạn văn nào giống câu truy vấn". Nó không cho biết "sự kiện nào đã xảy ra trước sự kiện nào", "nhân vật nào chưa được phép biết điều gì", "nếu bỏ sự kiện X thì sự kiện Y có còn xảy ra". Ba câu hỏi đó mới là bản chất của fanfic.

---

## 1. Trạng thái baseline (v1.1.3.1)

### Đã vững — giữ nguyên, không đập đi
- `TransactionManager` staging + fault injection 5/5 stage sạch tuyệt đối
- `rollback_to_chapter` 100% (snapshot là source of truth, trash để undo)
- `StateExtractor` regex: 5/5 test (không double-count, không nổ item, evidence phải là substring của draft)
- `build_sealed_packet` + `packet_hash` bind vào audit & commit
- CanonStore: 1.409 section → 4.355 chunk + FTS, `search_canon` hoạt động với cả truy vấn Việt và CJK
- `RiskProfiler.compute_risk`, fail-closed ở cả 3 risk level
- CLI: `init / ingest / write-next / rebuild-index / status / export`, `--require-canon` hoạt động

### Nợ kỹ thuật phải trả trong v2.0
| # | Nợ | Mức | Xử lý ở phase |
|---|---|---|---|
| D1 | `_check_timeline` luôn PASS (7 dòng, không có nhánh FAIL); `_check_frozen_canon` chỉ khớp keyword hard-code — nhưng registry ghi `implemented` | 🔴 Hồi quy an toàn | **P0** |
| D2 | Không có sự kiện canon, không có graph nhân quả | 🔴 Chặn năng lực cốt lõi | P1 |
| D3 | Không có thang cảnh giới / bất biến thế giới máy đọc được | 🔴 | P1 |
| D4 | Không có epistemic ledger (ai biết gì, từ chương nào) | 🔴 | P1 |
| D5 | Không đo được "hệ thống đã hiểu canon chưa" | 🔴 | P1 |
| D6 | Truy hồi phụ thuộc dấu tiếng Việt (query không dấu → 220 ký tự evidence vs 2.116 ký tự khi có dấu) | 🟠 | P1 |
| D7 | POD chỉ là điểm số cảm tính, không phải dữ liệu | 🔴 | P2 |
| D8 | Thay đổi không sinh hệ quả, hệ quả không có deadline | 🔴 | P2 |
| D9 | `RollingPlan.reconcile_horizon` sinh beat generic, macro plan không tự mở rộng | 🟠 | P4 |
| D10 | State extraction bằng regex → trần năng lực thấp ở arc lạ | 🟠 | P4 |
| D11 | Hybrid memory single-JSON; không crash-recovery từ journal khi khởi động | 🟡 | P4 |

---

## 2. Nguyên tắc thiết kế (bất di bất dịch)

1. **Fail-closed, và nhãn phải khớp hành vi.** Không tồn tại checker gắn nhãn `implemented` mà thân hàm không có nhánh FAIL. Có test tự động cấm điều này (P0-T3).
2. **Mọi phát biểu về canon phải có bằng chứng.** Mỗi fact/event/edge bắt buộc có `evidence` là **substring thật** của chunk canon + `source_chunk_id`. Không có evidence ⇒ không được ghi vào graph. (Tái dùng đúng nguyên tắc đã cứu BUG-06.)
3. **Deterministic ở lõi, LLM ở biên.** LLM chỉ đề xuất; validator xác định (regex/schema/substring/graph) mới được quyền ghi. Không bao giờ để LLM tự do ghi trực tiếp vào state.
4. **Kỷ luật thời gian canon.** Mọi truy hồi và mọi packet đều bị chặn theo `canon_time` và `epistemic_scope`. Nhân vật không được biết điều chưa xảy ra hoặc điều bị giữ kín.
5. **Thay đổi phải có giá.** Mọi divergence sinh ripple; ripple có `due_chapter`; ripple quá hạn = audit FAIL. Không cho phép "đổi rồi quên".
6. **Không đập lại thứ đang chạy tốt.** Transaction/rollback/extractor giữ nguyên API; tầng mới cắm vào qua interface.
7. **Mọi phase kết thúc bằng test đối kháng, không phải smoke test.** (Bài học từ 6 bug bị bỏ sót.)

---

## 3. Kiến trúc mục tiêu v2.0

```
fanfic_pipeline/
  core/                       # GIỮ NGUYÊN
    transaction_manager.py    ✅  story_state.py ✅  state_manager.py ✅
    context_builder.py        ✳️  (mở rộng packet v2)
    engine.py                 ✳️  (chèn 2 tầng mới vào write-next)
  packages/
    canon/                    🆕 PHẦN A — Hiểu nguyên tác
      alias_normalizer.py         chuẩn hoá danh xưng Việt/CJK/không dấu
      entity_extractor.py         nhân vật, tổ chức, địa danh, vật phẩm
      event_extractor.py          canon_event có bằng chứng
      canon_graph.py              node + edge nhân quả, truy vấn đồ thị
      power_ladder.py             thang cảnh giới + biên độ chiến lực
      frozen_invariants.py        bất biến không được phá
      epistemic_ledger.py         ai biết gì, từ chương nào, cấp bí mật
      canon_exam.py               BÀI THI CANON — đo "đã hiểu chưa"
    butterfly/                🆕 PHẦN B — Hiệu ứng cánh bướm
      pod.py                      Point of Divergence dữ liệu hoá
      causal_graph.py             precondition/effect, nhãn load-bearing
      propagator.py               lan truyền BFS + damping + inertia
      counterfactual.py           tính lại timeline canon sau POD
      divergence_ledger.py        sổ divergence + ripple + nợ hệ quả
      convergence.py              chính sách quán tính / hội tụ
    auditor/
      matrix_33.py              ✳️  registry v2
      checkers/                 🆕 checker thật, mỗi file 1 checker
  data/nhat_the_chi_ton/
    knowledge.py              ✳️  seed cho ladder + invariants
```

**Luồng `write-next` v2 (rút gọn):**

```
1. Xác định canon_time & mini_arc                → RollingPlan
2. Truy vấn canon graph + chunk (đã chuẩn hoá)   → CanonGraph + CanonStore
3. Lọc theo POD + counterfactual status          → Counterfactual
4. Lọc theo epistemic (ai được biết gì)          → EpistemicLedger
5. Lấy ripple đến hạn ở chương này               → DivergenceLedger
6. Đóng gói sealed packet v2 (+ packet_hash)     → ContextBuilder
7. Viết draft                                    → Writer
8. Trích state delta + divergence delta          → StateExtractor + POD
9. Audit v2 (canon fidelity + butterfly)         → Matrix v2
10. Commit atomic (state + graph + ledger)       → TransactionManager
```

Điểm chèn quan trọng: **bước 3, 4, 5 là toàn bộ giá trị của v2.0.** Bước 6–10 đã có sẵn.

---

## 4. Phân kỳ chi tiết

Ước lượng theo **ngày-người** (1 người + LLM assist, 1 ngày = ~6 giờ tập trung).

### P0 — Vá hồi quy an toàn *(1,5 ngày)* 🔴 LÀM TRƯỚC MỌI THỨ

Lý do đứng đầu: hiện tại 3 checker P0 gắn nhãn `implemented` nhưng trả PASS vô điều kiện. Nghĩa là **fail-closed đang bị vô hiệu hoá một cách vô hình** — nguy hiểm hơn cả bug fail-open cũ, vì bug cũ ít nhất còn lộ nhãn `stub`.

| Task | Nội dung | DoD |
|---|---|---|
| P0-1 | Viết thật `timeline_consistency` (spec §6.1) | FAIL được trên 6 ca âm; PASS trên 4 ca dương |
| P0-2 | Viết thật `frozen_canon` (spec §6.2), bỏ keyword hard-code, dùng alias normalizer tối giản | Bắt được "Khai Khiếu bay lượn" ở cả 3 biến thể chính tả + không dấu |
| P0-3 | **Test bất biến nhãn**: quét toàn registry, mọi checker `implemented` phải có ≥1 nhánh trả FAIL và phải FAIL trên fixture âm của chính nó | Test đỏ nếu ai đó relabel mà không implement |
| P0-4 | Nếu chưa viết kịp checker nào → trả nhãn về `stub` (⇒ UNKNOWN ⇒ REVISE) | Registry trung thực 100% |

### P1 — CANON MASTERY LAYER *(13 ngày)* 🔴 **Trọng tâm 1**

Mục tiêu đo được: **hệ thống trả lời đúng ≥85% bài thi canon 300 câu, trong đó nhóm temporal ≥80%.**

| Task | Nội dung | Ngày | Phụ thuộc |
|---|---|---|---|
| P1.1 | **Alias normalizer** — fold dấu, map CJK↔Hán-Việt (孟奇↔Mạnh Kỳ), biệt danh, đại từ tôn xưng; xây từ tần suất EPUB + LLM xác nhận; query expansion 2 chiều | 2 | — |
| P1.2 | **Entity extractor** — nhân vật / tổ chức / địa danh / vật phẩm / cảnh giới, có `first_seen_chapter`, `aliases[]`, `evidence` | 2 | P1.1 |
| P1.3 | **Event extractor** — canon_event có `actors, place, canon_chapter, preconditions, effects, evidence, necessity` (spec §A5). Chạy 2 pass: local → cross-chapter resolve | 3 | P1.2 |
| P1.4 | **Canon graph** — lưu + truy vấn (ancestors/descendants/depends_on), phát hiện mâu thuẫn nội tại | 2 | P1.3 |
| P1.5 | **Power ladder + frozen invariants** — thang cảnh giới có thứ tự, biên độ chiến lực, danh sách bất biến (seed tay + suy ra từ event) | 1,5 | P1.2 |
| P1.6 | **Epistemic ledger** — (fact, known_by, since_chapter, secrecy) + API `visible_to(actor, canon_time)` | 1,5 | P1.3 |
| P1.7 | **Canon Exam** — sinh 300 câu từ canon (factual / temporal / relational / rule / epistemic), chấm tự động, làm **cổng chặn** | 1 | P1.4, P1.6 |

**Cổng P1 (bắt buộc vượt mới sang P2):** `canon-exam` ≥85% tổng, ≥80% nhóm temporal, ≥90% nhóm rule. Không vượt ⇒ không được viết chương nào (`write-next` chặn giống `--require-canon`).

### P2 — BUTTERFLY EFFECT ENGINE *(11 ngày)* 🔴 **Trọng tâm 2**

Mục tiêu đo được: **1 POD nhân tạo → ≥1 canon event bị đánh `cannot_happen` đúng, ≥3 ripple sinh ra có deadline, và audit FAIL nếu ripple quá hạn hoặc nếu draft tham chiếu event đã sụp.**

| Task | Nội dung | Ngày | Phụ thuộc |
|---|---|---|---|
| P2.1 | **POD dữ liệu hoá** — `pod.json`: anchor, changed_facts, protected_invariants, scope, intensity | 1 | P1.4 |
| P2.2 | **Necessity labeling** — gán `load_bearing / contingent / incidental` cho từng canon event + edge (LLM đề xuất, người/heuristic chốt) | 2 | P1.4 |
| P2.3 | **Propagator** — BFS theo precondition, damping theo scope, sinh trạng thái `intact / weakened / broken / cannot_happen` | 2,5 | P2.1, P2.2 |
| P2.4 | **Counterfactual timeline** — bản canon "sau POD", cache + tính lại tăng dần khi có divergence mới | 1,5 | P2.3 |
| P2.5 | **Divergence ledger + ripple queue** — ripple có `due_chapter_range`, `tier`, `status`; nối vào `NarrativeDebtLedger` sẵn có | 2 | P2.3 |
| P2.6 | **Convergence policy** — quán tính theo scope (personal/local/faction/world), `butterfly_gain`, trần ripple mở | 1 | P2.4 |
| P2.7 | Tích hợp vào packet v2: bơm counterfactual + ripple đến hạn vào prompt | 1 | P2.4, P2.5 |

### P3 — AUDIT v2 *(5 ngày)*

| Task | Nội dung | Ngày |
|---|---|---|
| P3.1 | `canon_fidelity` — mọi phát biểu về canon trong draft phải khớp graph (hoặc là divergence đã đăng ký) | 1,5 |
| P3.2 | `canon_orphan` — draft tham chiếu event `cannot_happen` như đã xảy ra ⇒ FAIL | 1 |
| P3.3 | `butterfly_debt` — ripple quá hạn ⇒ FAIL; sắp hạn ⇒ REVISE | 1 |
| P3.4 | `divergence_monotonicity` — âm thầm quay lại canon sau khi đã lệch ⇒ FAIL | 0,5 |
| P3.5 | `pod_compatibility` viết lại thật, dựa graph thay vì cảm tính | 1 |

### P4 — Long-horizon *(8 ngày, sau khi đã viết được ~30 chương thật)*

| Task | Nội dung | Ngày |
|---|---|---|
| P4.1 | State extractor LLM + JSON schema, regex thành validator chéo (giữ nguyên rule evidence-substring) | 2,5 |
| P4.2 | `RollingPlan` tự mở rộng arc: causal-chain + promises/payoffs thay cho beat generic | 2,5 |
| P4.3 | Hybrid memory → SQLite (ngưỡng ~200 chương) | 2 |
| P4.4 | Crash-recovery từ journal khi khởi động | 1 |

### P5 — Vận hành *(3 ngày)*

| Task | Nội dung | Ngày |
|---|---|---|
| P5.1 | CLI v2: `canon build-graph / canon-exam / pod set / butterfly status / ripple list` | 1 |
| P5.2 | HITL console: xem packet, xem ripple đến hạn, phê duyệt divergence | 1 |
| P5.3 | Drift monitor: khoảng cách canon, entropy khẩu khí, tỉ lệ REVISE theo chương | 1 |

---

## 5. Thứ tự & phụ thuộc

```
P0 ──► P1.1 ──► P1.2 ──┬─► P1.3 ──► P1.4 ──┬─► P1.7 (CỔNG) ──► P2.1 ──► P2.2 ──► P2.3 ──┬─► P2.4 ──┬─► P2.7 ──► P3 ──► [VIẾT THẬT] ──► P4 ──► P5
                       │                   │                                            └─► P2.5 ──┘
                       └─► P1.5            └─► P1.6 ─────────────────────────────────────► P2.6
```

**Tổng: ~41,5 ngày-người** cho P0→P5. Đường tới mốc "viết được thật" (P0+P1+P2+P3) = **30,5 ngày**.

Có thể chạy song song nếu 2 người: nhánh canon (P1.1→P1.4) và nhánh luật thế giới (P1.5, P1.6) độc lập sau P1.2.

---

## 6. Định nghĩa "đủ để viết fanfic" — 3 mốc

### M1 — Viết được 1 arc có kiểm soát *(sau P0 + P1 + P2.1–P2.5)*
- `canon-exam` ≥85%
- 1 POD đăng ký, propagator sinh ripple đúng
- Viết 10 chương chế độ HITL, người duyệt từng chương
- **Tiêu chí đạt:** 0 lỗi canon nghiêm trọng do người soát tìm ra trong 10 chương; ≥8/10 chương pass audit ngay lần đầu hoặc sau 1 revise

### M2 — 50 chương bán tự động *(sau P3)*
- Audit v2 đủ 4 checker butterfly + canon_fidelity
- Người chỉ duyệt chương có `risk = HIGH` hoặc có ripple đến hạn
- **Tiêu chí đạt:** ≤5% chương phải rollback; 100% ripple được trả trong `due_chapter_range`; drift khẩu khí trong ngưỡng

### M3 — 500+ chương tự động *(sau P4)*
- State extractor LLM, plan tự mở rộng, SQLite memory, crash recovery
- **Tiêu chí đạt:** chạy liên tục 100 chương không cần can thiệp tay; canon-exam re-run vẫn ≥85%; số ripple mở không tăng đơn điệu (không phình nợ)

---

## 7. Kiểm thử & nghiệm thu (chuẩn đối kháng)

Sau bài học 6 bug bị bỏ sót, mọi phase nghiệm thu theo 4 lớp, **không nhận smoke test làm bằng chứng**:

1. **Test bất biến cấu trúc** — nhãn khớp hành vi (P0-3); mọi entity trong graph có evidence là substring thật; mọi ripple có deadline.
2. **Test đối kháng (negative fixtures)** — mỗi checker phải có ≥3 fixture âm mà nó **buộc phải FAIL**. Checker không FAIL được trên fixture âm của chính nó = chưa tồn tại.
3. **Fault injection** — mở rộng `FANFIC_FAULT_INJECT` sang commit của graph + ledger; dừng ở mọi stage, so hash toàn thư mục, yêu cầu "NONE (atomic OK)".
4. **Butterfly regression suite** — bộ POD mẫu + kỳ vọng cố định; mỗi lần sửa propagator phải cho ra đúng tập `cannot_happen` và đúng số ripple.

Bảng nghiệm thu chi tiết từng ca: xem **SPEC §8**.

---

## 8. Rủi ro & giảm thiểu

| Rủi ro | Xác suất | Tác động | Giảm thiểu |
|---|---|---|---|
| Trích xuất 1.409 chương tốn token/thời gian lớn | Cao | Trung bình | Chỉ trích xuất sâu vùng canon liên quan POD (±50 chương) trước; phần còn lại trích nông (entity + event tiêu đề). Cache theo `chunk_hash`, không trích lại |
| LLM bịa canon event | Cao | 🔴 Nặng | Bắt buộc evidence-substring; event không khớp bị loại; đo tỉ lệ loại như metric chất lượng |
| Propagator lan truyền quá đà (mọi thứ đều `broken`) | Trung bình | Nặng | Damping + inertia theo scope + nhãn `incidental` không lan; trần độ sâu BFS; test regression |
| Propagator quá nhu nhược (không gì đổi) | Trung bình | Nặng | Fixture bắt buộc: POD epistemic phải phá ≥1 event load-bearing |
| Nợ ripple phình vô hạn ở chương 300+ | Trung bình | Trung bình | Trần `max_open_ripples`; ripple quá hạn chặn write-next |
| Nhãn `implemented` giả tái diễn | **Đã xảy ra 2 lần** | Nặng | P0-3 làm test bắt buộc trong CI |
| Canon exam bị overfit (sinh câu dễ) | Trung bình | Trung bình | Sinh câu từ chunk *ngẫu nhiên có phân tầng*, giữ 20% làm held-out không dùng khi tune |

---

## 9. Ngân sách vận hành (ước lượng)

| Hạng mục | Khối lượng | Ghi chú |
|---|---|---|
| Trích xuất canon sâu (300 chương quanh POD) | ~1,2M token input | Một lần, cache theo chunk_hash |
| Trích xuất nông (1.109 chương còn lại) | ~0,8M token | Chạy nền, có thể hoãn |
| Canon exam (300 câu × 2 lượt) | ~0,3M token | Mỗi lần đổi retrieval mới re-run |
| Mỗi chương fanfic (packet + draft + audit + revise) | ~25–40k token | Nhân với số chương để dự toán |
| 1.000 chương | ~30M token | Cần theo dõi bằng drift monitor P5.3 |

---

## 10. Bảng tổng hợp task → file → test

| Task | File tạo/sửa | Test nghiệm thu |
|---|---|---|
| P0-1 | `auditor/checkers/timeline_consistency.py` | `test_timeline_negative.py` (6 ca âm) |
| P0-2 | `auditor/checkers/frozen_canon.py` | `test_frozen_negative.py` (3 biến thể chính tả) |
| P0-3 | `tests/test_registry_honesty.py` | Quét registry, ép FAIL trên fixture âm |
| P1.1 | `canon/alias_normalizer.py` | Query không dấu ≥90% chất lượng so với có dấu |
| P1.2–P1.4 | `canon/entity_extractor.py`, `event_extractor.py`, `canon_graph.py` | 100% node có evidence substring thật |
| P1.5 | `canon/power_ladder.py`, `frozen_invariants.py` | Thang cảnh giới có thứ tự toàn phần, không vòng |
| P1.6 | `canon/epistemic_ledger.py` | `visible_to()` không rò fact tương lai (test spoiler) |
| P1.7 | `canon/canon_exam.py` | ≥85% / temporal ≥80% / rule ≥90% |
| P2.1–P2.6 | `butterfly/*` | Butterfly regression suite (SPEC §8.3) |
| P2.7 | `core/context_builder.py` | Spy test: packet chứa counterfactual + ripple đến hạn |
| P3.1–P3.5 | `auditor/checkers/*` | Mỗi checker ≥3 fixture âm FAIL |
| P4.1–P4.4 | `core/*`, `memory/*` | Fault injection mở rộng + crash recovery test |

---

## 11. Việc nên làm ngay tuần này

1. **P0 toàn bộ** (1,5 ngày) — vá hồi quy, dựng test bất biến nhãn.
2. **P1.1 alias normalizer** (2 ngày) — rẻ, độc lập, và sửa luôn điểm yếu truy hồi không dấu đã đo được.
3. **P1.3 trích xuất event thử trên 20 chương canon** — để hiệu chỉnh schema trước khi đốt token cho 300 chương.

Sau 3 việc này bạn sẽ biết chi phí thật của P1 và có thể chốt lịch phần còn lại bằng số liệu thật thay vì ước lượng.
