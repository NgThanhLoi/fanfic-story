"""
P4.4 — Crash Recovery: đọc journal (BEGIN/COMMIT/ABORT) khi khởi động, sửa nếu dang dở.
- Nếu có BEGIN không có COMMIT/ABORT tương ứng -> rollback staging đó
"""
import json, pathlib
from typing import List, Dict, Any

def recover_from_journal(journal_path: str, project_dir: str) -> Dict[str,Any]:
    p = pathlib.Path(journal_path)
    if not p.exists():
        return {"recovered": 0}
    lines = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    # Find BEGIN without matching COMMIT/ABORT
    by_tx: Dict[str, List[Dict]] = {}
    for rec in lines:
        tid = rec.get("tx_id")
        if tid: by_tx.setdefault(tid, []).append(rec)
    dangling=[]
    for tid, recs in by_tx.items():
        phases={r.get("phase") for r in recs}
        if "BEGIN" in phases and not ({"COMMIT","COMMITTED"} & phases) and "ABORTED" not in phases:
            dangling.append(tid)
    # Cleanup staging dirs for dangling
    for tid in dangling:
        staging = pathlib.Path(project_dir)/"transactions"/f"staging_{tid}"
        if staging.exists():
            import shutil
            shutil.rmtree(staging, ignore_errors=True)
    return {"dangling": dangling, "recovered": len(dangling)}
