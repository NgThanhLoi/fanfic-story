# Fanfic Pipeline v2.0

Pipeline AI viết fanfic tiếng Việt cho **Nhất Thế Chi Tôn (一世之尊)** — canon-grounded, fail-closed, có governance layer hợp nhất từ package tham chiếu `yishizhizun-fanfic` (spec: `docs/specs/2026-08-21-reference-merge-design.md`).

## Install
```bash
pip install -r requirements.txt
```

## Quick start
```bash
python fanfic_pipeline/fanfic_cli.py init --project demo --title "Nhất Thế Chi Tôn: Fanfic" --mode auto
python fanfic_pipeline/fanfic_cli.py ingest --project demo --epub /path/to/一世之尊.epub
python fanfic_pipeline/fanfic_cli.py readiness --project demo          # gate READY|BLOCK trước khi viết
python fanfic_pipeline/fanfic_cli.py write-next --project demo --force-auto   # demo mode không cần API key
python fanfic_pipeline/fanfic_cli.py doctor --project demo             # kiểm tra chain + manifest
python fanfic_pipeline/fanfic_cli.py audit --all --project demo        # derive chương từ committed chain
```

## Governance (P0)
- **Premise validation** (`packages/governance/premise.py`): planning artifact phải qua canon-validate (transition topology + domain-fill guard) TRƯỚC khi trở thành đầu vào tin cậy — bài học FC36 "pipeline enforce đúng premise sai vẫn ra chương sai".
- **Readiness gate** (`readiness.py`): `READY` mới được DRAFT; BLOCK liệt kê blockers. Không draft chỉ vì user bảo "viết tiếp".
- **Subsystem registry + compliance**: mỗi chương kê khai từng subsystem với `USED` / `ROUTED_OFF_WITH_REASON` / `N/A_WITH_REASON` / `BLOCK`; fake-USED (không evidence hash) bị audit bắt.
- **Provenance chain**: commit ghi `timeline/event_map.jsonl` + regenerate `MANIFEST_SHA256.json`; `doctor` soi lệch head/manifest.
- **Runtime policy** (`runtime_policy.json`): tắt layer phải ra receipt — cấm silent fallback.

## Audit gate — 26 checkers fail-closed
Mới trong v2.0: `meta_leak`, `epistemic_claim`, `transition_topology`, `domain_fill`, `style_fingerprint` (2 mode), `identity_reveal`, `bounded_progression`, `combat_style`; viết lại `ooc_fidelity` (voice rules), `relationship_dynamics` (nhịp quan hệ theo committed state). Checker `implemented` không có nhánh FAIL thật = test đỏ.

## Retrieval & Intel
- **VI canon store** (`packages/retrieval/vi_canon.py`): FTS5 chuẩn-hóa-không-dấu trên 13.5k chunks canon tiếng Việt — query có dấu ≡ không dấu (hết nợ D6); temporal boundary `as_of_chapter`.
- **LSA router + style profile** (`style_profile.py`): fingerprint là dẫn xuất tính từ corpus (`refingerprint --from-ch A --to-ch B`); 2 chế độ văn phong:
  - `fanfic_voice` (mặc định): guard band chống trôi.
  - `canon_mimicry`: giống tác giả gốc, gate `style_fidelity ≥ canon_min_fidelity` (mặc định 90).
- **Intel** (`packages/intel/`): identity coreference (bí danh spoiler-gated theo `reveal_chapter`), capability timeline (ai biết gì ở canon ch.N), Social Web theo arc, OC Power System (availability ≠ acquisition ≠ mastery; survival floor nhiệm vụ tử địa), ArcLedger (no personality drift without causal receipt).

## Notes
- `CanonStore` populated via `ingest` (SpineAwareEpubParser -> FTS5). `write-next` uses RAG from ingested canon.
- Audit gate is fail-closed. `--force-auto` allows REVISE->commit with warning (dry-run only).
- Pydantic v2: `.model_dump()` preferred, `.dict()` still works (deprecated).
- Reference package `docs/references/yishizhizun-fanfic/` là read-only — runtime không bao giờ import từ đó (có test guard).
