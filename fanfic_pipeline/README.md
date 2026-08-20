# Fanfic Pipeline v1.1.1

## Install
```bash
pip install -r requirements.txt
```

## Quick start
```bash
python fanfic_pipeline/fanfic_cli.py init --project demo --title "Nhất Thế Chi Tôn: Fanfic" --mode auto
python fanfic_pipeline/fanfic_cli.py ingest --project demo --epub /path/to/一世之尊.epub
python fanfic_pipeline/fanfic_cli.py write-next --project demo --force-auto
```

## Notes
- `CanonStore` populated via `ingest` (SpineAwareEpubParser -> FTS5). `write-next` uses RAG from ingested canon.
- Audit gate is fail-closed: needs `ConsistencyVerificationStack` PASS. `--force-auto` allows REVISE->commit with warning (dry-run only).
- Pydantic v2: `.model_dump()` preferred, `.dict()` still works (deprecated).
