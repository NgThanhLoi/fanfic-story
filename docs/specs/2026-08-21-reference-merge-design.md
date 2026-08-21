# Merge yishizhizun-fanfic vào fanfic_pipeline — Thiết kế v1.0

- **Ngày:** 2026-08-21
- **Nguồn tham chiếu:** `docs/references/yishizhizun-fanfic/` (package do GPT 5.6 Sol build & tự chạy, FC1–FC35 committed; review nội bộ `YZSZ_DETAILED_REVIEW_FC36_AND_WORKSPACE_2026-08-21.md` là đầu vào thiết kế bắt buộc)
- **Phạm vi:** gộp toàn bộ — governance + checkers + retrieval + intel nâng cao (Social Web, OC Power, Fate 4-lớp-sự-thật) + dữ liệu tri thức canon. Tích hợp native vào `fanfic_pipeline`, KHÔNG subprocess ra tool của reference.
- **Xác nhận:** test đối kháng từng phase + smoke dry-run end-to-end (không API key).
- **Ngoài phạm vi:** nhập nội dung fanfic-cụ-thể của reference (FC specs, OC Thiên Diện bible, arc outlines) — chỉ giữ làm ví dụ trong `docs/references/`; xuất bản; đa fandom.

---

## 0. Invariant xuyên suốt (mỗi invariant ≥ 1 test đối kháng)

| # | Invariant | Nguồn bài học |
|---|---|---|
| INV-1 | **Premise trước enforce** — planning artifact (chapter spec, outline, scene dossier) chưa qua canon-validate không được làm đầu vào tin cậy của bất kỳ gate nào | Review §2.3, §23: "pipeline enforce rất nghiêm một premise sai vẫn ra chương sai" (FC36: Nhãn Khiếu → nhảy cóc Tỵ Khiếu, mọi gate vẫn READY/PASS) |
| INV-2 | **Single-source head** — durable head chỉ đọc từ project meta (`current_chapter` + snapshot chain); cấm hard-code head trong docs/spec/bootstrap | Review F-05/F-08: bootstrap ghi FC12, handoff ghi FC34, thực tế FC35 |
| INV-3 | **Không silent fallback** — layer tùy chọn bị tắt phải xuất hiện với status `ROUTED_OFF_WITH_REASON`; báo `USED` khi thực chất fallback = fail test | Reference PRODUCTION_CHAPTER_PIPELINE "Hard failures"; runtime_policy.json |
| INV-4 | **Provenance chain** — draft SHA ↔ prewrite receipt SHA ↔ snapshot ↔ compliance report; manifest SHA-256 regenerate ở mỗi commit, verify lệnh độc lập | Review F-06/F-07: manifest stale 20 file sau FC35 |
| INV-5 | **Audit derive, không hard-code** — mọi lệnh audit/compliance lấy danh sách chương từ committed chain + chapter specs; hard-code range cấm | Review F-04: `audit --all` chỉ audit FC1–10 |
| INV-6 | **Fail-closed + nhãn khớp hành vi** — checker `implemented` phải có nhánh FAIL thật; UNKNOWN ở severity P0 ⇒ REVISE | Nguyên tắc #1/#7 của PLAN v2.0, mở rộng cho 8+3 checker mới |
| INV-7 | **Deterministic ở lõi, LLM ở biên** — LLM chỉ đề xuất; validator regex/schema/substring/graph mới được ghi state hay chặn commit | Nguyên tắc #3 PLAN v2.0 |
| INV-8 | **Thay đổi phải có giá + có nguyên nhân** — divergence sinh ripple có deadline; thay đổi tính cách/quan hệ giữa 2 chương phải truy nguồn về sự kiện đã commit ("no personality drift without causal receipt") | PLAN v2.0 nguyên tắc #5 + khe hở OOC phát hiện khi rà 5 trục |

## 1. Kiến trúc mục tiêu

```
fanfic_pipeline/
├─ fanfic_cli.py                      [SỬA] +readiness · policy · compliance · doctor · audit --all (derive)
├─ web_studio.py                      [SỬA] /api/status trả readiness + compliance gần nhất
├─ core/
│  ├─ engine.py                       [SỬA] run_chapter_step chèn Premise-Validation → Readiness Gate trước planner
│  ├─ state_manager.py                [SỬA] quản lý runtime_policy, prewrite/, compliance/, timeline/event_map
│  ├─ transaction_manager.py          [GIỮ API] commit-hook: snapshot như cũ + trigger compliance & manifest regen
│  └─ (ideator, hierarchical_planner, story_state, model_router…)  [GIỮ NGUYÊN]
├─ packages/
│  ├─ governance/                     ★ MỚI
│  │  ├─ premise.py                         INV-1: canon-validate planning artifact trước khi tin
│  │  ├─ readiness.py                       gate READY|BLOCK (premise đã validate + foundation + chain)
│  │  ├─ registry.py                        subsystem registry; per-chapter USED/ROUTED_OFF_WITH_REASON/N/A/BLOCK
│  │  ├─ policy.py                          runtime_policy.json — layer on/off, off ⇒ receipt
│  │  └─ compliance.py                      report 4 nhóm Canon/Power/Pipeline/State + manifest freshness
│  ├─ intel/                          ★ MỚI
│  │  ├─ topology.py                        canonical transition graph (khiếu mắt→tai→mũi→miệng…) evidence-grounded;
│  │  │                                     exception phải có receipt; chạy ở READINESS (F-09)
│  │  ├─ identity.py                        bí danh zh↔vi theo reveal_chapter; spoiler-sensitive fail-closed
│  │  ├─ capability.py                      time-indexed character facts + future-awareness profile;
│  │  │                                     tách 4 lớp sự thật (biết / suy-diễn / bàn-tay-giấu / spoiler-planner)
│  │  ├─ social_web.py                      bible quan hệ theo arc; spec khai social_targets, thiếu = BLOCK;
│  │  │                                     writer chỉ thấy beat hiện tại, planner thấy trajectory
│  │  ├─ oc_power.py                        availability ≠ acquisition ≠ mastery ≠ realm; survival-floor nhiệm vụ tử địa
│  │  ├─ arc_ledger.py                      sổ phát triển nhân vật: mọi drift tính cách/quan hệ gắn causal receipt (INV-8)
│  │  └─ ledgers.py                         foreshadowing / promises / emotional debts / threads → inject context
│  ├─ retrieval/                      ★ MỚI
│  │  ├─ vi_canon.py                        corpus canon VI: FTS5 chuẩn-hóa-không-dấu (nợ D6) + BM25
│  │  ├─ lsa.py                             vector chương VI/ZH từ .npy (numpy-only)
│  │  ├─ style_profile.py                   ★ style modes + similarity scoring (xem §4.4)
│  ├─ auditor/
│  │  ├─ registry.py                  [SỬA] DEFAULT_CHECKERS mở rộng (bảng §2)
│  │  └─ checkers/                    ★ 11 checker mới (bảng §2); viết lại ooc_fidelity, relationship_dynamics
│  ├─ canon/ memory/ enrichment/ style/ butterfly/ worker/   [GIỮ NGUYÊN]
│  └─ (power_ladder giữ API; topology nâng cấp phần so-khop bên dưới)
├─ data/nhat_the_chi_ton/             [NHẬP ~80MB JSONL/YAML/MD từ reference; *.db gitignore, regenerate từ chunks]
│  ├─ vi_canon/                             chunks.jsonl + chapters.jsonl + glossary.jsonl
│  ├─ style/style_fingerprint.json          dẫn xuất (xem §4.3), KHÔNG copy số liệu đo sẵn
│  ├─ identity_registry.jsonl               bí danh + reveal_chapter + source_chunks evidence
│  ├─ capability_timeline.jsonl             time-indexed character facts
│  └─ aperture_topology.json                graph chuyển-khiếu có evidence (trích corpus, chuẩn review §5)
├─ storage/projects/<id>/             [project-scoped runtime]
│  ├─ runtime_policy.json                   route on/off dense/reranker…
│  ├─ prewrite/<chapter>/                   context-pack slices + PREWRITE_RECEIPT (SHA-256 từng slice)
│  ├─ timeline/event_map.jsonl              ★ dual timeline materialized (xem §3)
│  ├─ compliance/<chapter>_*.json           report + subsystem statuses + manifest freshness
│  └─ snapshots/ transactions/              [CÓ SẴN — atomic + rollback giữ nguyên]
tests/                                ★ test đối kháng theo phase
docs/references/yishizhizun-fanfic/   [GIỮ — tham chiếu; runtime KHÔNG BAO GIỜ import từ đây]
```

## 2. Checker mới / viết lại (deterministic, fail-closed)

| Checker | Severity | Chức năng | Nguồn tham khảo |
|---|---|---|---|
| `meta_leak` ★ | P0 | Văn không chứa nhãn ngoài-vùng-truyện ("canon", planner/writer/receipt/snapshot, PASS/FAIL/READY/BLOCK, "quỹ đạo vốn có"…); strong hit = FAIL | tools_meta_leak_check.py |
| `epistemic_claim` ★ | P0 | Thay EpistemicLeakChecker: giả thuyết planner, tên phe/địa điểm chưa tiết lộ, năng lực tương lai không được assert thành fact; rò spoiler-planner vào thoại nhân vật = FAIL | tools_epistemic_claim_check.py + Fate spec |
| `transition_topology` ★ | P0 | Skip bước cảnh giới/khai khiếu ngoài topology canon mà không có exception receipt = FAIL (mirror draft-side của premise gate) | Review F-09 |
| `style_fingerprint` ★ | P0 | Guard band percentile câu/đoạn/dialogue-ratio; mode `fanfic_voice`: FAIL luôn chặn, REVIEW chặn trừ khi có style_manual_review receipt; cấm từ Anh lạ. Mode `canon_mimicry`: thêm style fidelity ≥ ngưỡng (mặc định 90) — xem §4.4 | tools_style_check.py + style_profile.py |
| `identity_reveal` ★ | P0 | Bí danh spoiler-sensitive xuất hiện trước reveal_chapter = FAIL (intra-chapter fail-closed) | identity_registry.jsonl |
| `ooc_fidelity` ⟳ | P0 | Viết lại từ stub: driver từ voice profile — ma trận xưng hô/hào khí theo cặp nhân vật, hành động-bị-cấm theo trạng thái; violation phải trích evidence span; LLM-critic chỉ còn advisory | Khe hở trục nhân vật |
| `relationship_dynamics` ⟳ | P1 | Nhịp quan hệ trong draft phải khớp intimacy_level/current_dynamic committed; tiến nhanh hơn mà không có sự kiện chứng cứ trong chương = FAIL | Khe hở trục nhân vật |
| `bounded_progression` ★ | P1 | Sensory/power payoff ≤ envelope committed state; cấm intent-erasure / siêu nhiên hóa kỹ năng bounded (bài học wording Tàng Ý) | Review F-03, §8 |
| `combat_style` ★ | P2 | Profile chiến đấu theo mốc thời gian; required_or_na | tools_combat_style_check.py |

(★ mới, ⟳ viết lại. Registry cuối: 19 hiện có − `epistemic_leak` nghỉ thay bằng `epistemic_claim` + 8 checker mới = **26 checker**; trong đó 3 được viết lại đáng kể: `epistemic_claim`, `ooc_fidelity`, `relationship_dynamics`.)

## 3. Dual timeline materialized

Artifact: `storage/projects/<id>/timeline/event_map.jsonl` — transaction manager ghi 1 dòng mỗi commit:

```json
{"fic_ch": 13, "canon_anchors_consumed": ["CT-0115", "CT-0116"],
 "divergences_registered": ["DIV:SEED001"], "epistemic_updates": [...],
 "snapshot": "S0013-after-ch013", "draft_sha256": "…"}
```

Consumer: readiness (predecessor chain), checker timeline (`canon_time_max` suy ra từ anchors đã tiêu thụ thay vì đoán từ outline), doctor (INV-2 đối chiếu head).

## 4. Dữ liệu nhập từ reference

### 4.1 Nhập thẳng (fandom-level truth)
Canon VI (`01_canon/vi/` chunks + chapters + glossary), entities/timeline JSONL, `identity_registry.jsonl`, `capability_timeline.jsonl`, voice profiles YAML, narrative ledger schemas (foreshadowing/promises/debts/threads — schema nhập, dữ liệu khởi tạo rỗng cho project mình). DB lớn gitignore, regenerate từ chunks.

### 4.2 Chỉ dùng làm template
OC Power System + survival floor (cơ chế port native, dữ liệu OC của họ bỏ), Social Web arc bibles (schema port, dữ liệu Arc-01..04 bỏ), chapter specs / scene dossiers (format port).

### 4.3 Fingerprint văn phong là dẫn xuất
`style_fingerprint.json` tính lại từ corpus VI vừa nhập qua lệnh `style refingerprint --from-ch A --to-ch B` (window chọn được); số liệu đo-sẵn của reference chỉ dùng sanity-check công cụ tính.

### 4.4 Chế độ văn phong — `style_profile.py` (yêu cầu user: tùy chọn "giống tác giả gốc ≥ 90%")

Hai chế độ cấu hình qua `runtime_policy.json` (`style.mode`), đổi được giữa chừng mà không đụng code:

- **`fanfic_voice`** (mặc định) — fingerprint tính từ corpus VI (§4.3) làm **guard band** chống trôi: draft phải nằm trong percentile band của nguyên tác, không cấm nét riêng. Giống hiện tại + checker style.
- **`canon_mimicry`** — mục tiêu giống tác giả gốc tối đa. Ba lớp:
  1. **Context**: retrieval ưu tiên evidence cùng arc/mốc canon của chương đang viết; writer prompt kèm excerpt mẫu văn cùng cảnh-loại (combat/đối thoại/nội tâm) từ chính corpus VI — LLM bắt chước trên dữ liệu thật, không mô tả suông.
  2. **Measure**: similarity score giữa draft và fingerprint gốc trên bộ metric đầy đủ (percentile câu/đoạn, dialogue-ratio, dialogue_attached_narration_ratio, comma density, top-k function-word & bigram distribution, độ dài thoại, nhịp cảnh-và-lời).
  3. **Gate**: `style_fidelity = max(0, 100 − weighted_distance)`; ngưỡng chặn lấy từ `runtime_policy.json` → `style.canon_min_fidelity`, mặc định **90**. Dưới ngưỡng ⇒ REVISE kèm directive chỉ ra metric nào lệch và lệch hướng nào (quá dài/quá ngắn/thiếu thoại…). Trong mode này REVIEW cũng chặn như FAIL (không có lối thoát manual-review cho khoảng cách văn phong).

Đo lường "≥90%": điểm là **weighted distance** có chuẩn hóa, không phải con số cảm tính — mỗi metric quy về z-score/percentile-offset rồi tổng hợp theo trọng số khai báo trong fingerprint; công thức và trọng số ghi trong `style_fingerprint.json` để kết quả tái lập được. Test đối kháng P2: (a) đoạn văn tiếng Anh/kiểu dịch máy cứng phải <90 ⇒ REVISE; (b) excerpt thật của nguyên tác đưa vào checker phải ≥95 (calibration); (c) đổi mode phải phản ánh ngay vào receipt subsystem registry (`USED` với mode nào).
`style_fingerprint.json` tính lại từ corpus VI vừa nhập qua lệnh `style refingerprint --from-ch A --to-ch B` (window chọn được); số liệu đo-sẵn của reference chỉ dùng sanity-check công cụ tính.

## 5. Luồng run_chapter_step sau merge

```
PRELOAD (state, voices, ledgers, event_map)
  → PREMISE VALIDATION (governance/premise + intel/topology + domain-fill trên spec/outline/dossier)
      sai canon ⇒ BLOCK — sửa foundation, cấm improvising prose
  → READINESS GATE (foundation đủ, predecessor chain liền kề qua event_map,
      runtime_policy routing, survival-floor nếu nhiệm vụ tử địa)
      BLOCK ⇒ liệt kê blockers
  → PRE-DRAFT CONTEXT PACK (vi_canon BM25/FTS + LSA song ngữ, identity, capability,
      social_web, oc_power, ledgers; style_mode từ runtime_policy — canon_mimicry kèm
      excerpt mẫu cùng arc + cảnh-loại; hash-bind slice ⇒ PREWRITE_RECEIPT)
  → DRAFT (planner + writer qua model_router; demo-mode dry-run vẫn chạy đủ tầng deterministic)
  → AUDIT GATE fail-closed (26 checker)
  → USER APPROVAL (duyệt văn bản ≠ commit)
  → COMMIT (transaction manager: atomic + snapshot + rollback — giữ nguyên API)
  → POST-COMMIT (compliance report 4 nhóm + subsystem statuses + event_map append
      + regenerate SHA-256 manifest + arc_ledger cập nhật)
```

## 6. Phases thực thi — mỗi phase kết thúc bằng test đối kháng

| Phase | Nội dung | Test đối kháng bắt buộc |
|---|---|---|
| P0 Governance + data | Import data, premise/readiness/registry/policy/compliance, event_map, CLI, doctor | Gate BLOCK khi thiếu foundation; fake-USED bị bắt; head lệch giữa meta và docs bị doctor soi ra; audit --all derive đúng N chương giả (40) |
| P1 Checkers | 10 checker bảng §2 + registry-honesty | Mỗi checker có case FAIL thật; checker implemented không nhánh FAIL = test đỏ; skip-aperture bị transition_topology chặn; TCM-fill bị domain_fill chặn |
| P2 Retrieval | vi_canon FTS không dấu + BM25 + LSA; refingerprint; `style_profile.py` 2 mode + similarity scoring | Query không dấu ≡ có dấu (hết nợ D6); refingerprint tái lập fingerprint trong dung sai; style fidelity: excerpt thật ≥95, văn dịch-máy <90 ⇒ REVISE; đổi mode hiện trong subsystem receipt |
| P3 Intel | identity/capability/social_web/oc_power/arc_ledger/ledgers + cắm checker liên quan | Spoiler-reveal bị chặn; candidate leak bị chặn; survival-floor BLOCK nhiệm vụ tử địa thiếu receipt; personality-drift không receipt bị ooc/relationship chặn |
| P4 E2E | Provenance binding, smoke dry-run toàn pipeline, docs | Smoke không-API-key chạy write-next đủ tầng; provenance draft↔receipt khớp SHA; manifest mismatch = 0 sau commit |

## 7. Đã cân nhắc và chốt

- **Kích thước:** nhập ~250MB; chỉ JSONL/YAML/MD (~80MB) commit, DB regenerate.
- **Không đập thứ đang chạy:** transaction/rollback/butterfly/audit-runner giữ API; tầng mới cắm qua registry + context packet (nguyên tắc #6 PLAN v2.0).
- **Dry-run-first:** mọi cơ chế deterministic, smoke không cần API key.
- **Reference là read-only:** runtime import cấm từ `docs/references/`; test có guard cấm path đó trong sys.path của pipeline.
