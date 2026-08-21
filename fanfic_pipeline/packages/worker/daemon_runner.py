"""
Background Task Daemon & Autonomous Batch Worker:
Enables long-running multi-chapter autonomous production loops (similar to 'inkos up').
Features:
- Token budget management
- Auto-retry on rate limits with exponential backoff
- Safe chapter commit & rollback transactions
- Event emitter for live SSE streaming to Web UI
"""

import time
import json
from typing import Callable, List, Dict, Any, Optional

class ProductionTask:
    def __init__(self, task_id: str, project_id: str, target_chapters_count: int, author_instruction_template: str = ""):
        self.task_id = task_id
        self.project_id = project_id
        self.target_chapters_count = target_chapters_count
        self.author_instruction_template = author_instruction_template
        self.status = "pending"  # pending, running, paused, completed, failed
        self.completed_chapters = 0
        self.logs: List[str] = []
        self.start_time = None
        self.end_time = None

class DaemonWorker:
    def __init__(self, engine, state_mgr):
        self.engine = engine
        self.state_mgr = state_mgr
        self.current_task: Optional[ProductionTask] = None
        self.is_running = False

    def start_batch_job(self, task_id: str, count: int, instruction: str = "", listener: Optional[Callable] = None):
        meta = self.state_mgr.load_project_meta()
        start_ch = meta.get("current_chapter", 0) + 1
        
        self.current_task = ProductionTask(task_id, self.state_mgr.project_id, count, instruction)
        self.current_task.status = "running"
        self.current_task.start_time = time.time()
        self.is_running = True

        for i in range(count):
            if not self.is_running:
                self.current_task.status = "paused"
                break

            target_ch = start_ch + i
            log_msg = f"🚀 [DAEMON WORKER] Bắt đầu tự động sản xuất Chương {target_ch} ({i+1}/{count})..."
            self.current_task.logs.append(log_msg)
            if listener:
                listener({"type": "progress", "message": log_msg, "chapter": target_ch})

            try:
                # v1.1: same tx contract as CLI/Web — fail-closed commit
                result = self.engine.run_chapter_step(target_ch, author_instruction=instruction)
                # backward compat: engine may return 3 or 4 values
                if len(result)==4: outline, draft, critique, state_delta = result
                else: outline, draft, critique = result; from fanfic_pipeline.core.story_state import StoryStateManager as _SSM; state_delta = _SSM.extract_state_delta = StoryStateManager.extract_state_delta(target_ch, draft.content, self.state_mgr.load_story_state())
                # Build audit receipt for gate — reuse receipt from run_chapter_step; re-audit only if hash mismatch
                receipt = getattr(self.engine, 'last_audit_receipt', None)
                if receipt is None or getattr(receipt, 'draft_hash', None) != self.state_mgr.calculate_draft_hash(draft.content):
                    from fanfic_pipeline.packages.auditor.base import AuditContext
                    receipt = self.engine.audit_runner.evaluate(
                        draft.content,
                        AuditContext(chapter_num=target_ch, draft_text=draft.content,
                                     current_state=self.state_mgr.load_story_state(),
                                     canon_store=self.engine.canon_store,
                                     enrichment_store=self.engine.enrichment_store,
                                     ledger=self.engine.ledger,
                                     writer_packet=getattr(self.engine, '_last_packet', None))
                    )
                # Use transactional commit (fail-closed) — not direct state_mgr.commit_chapter
                # If receipt is REVISE/BLOCK, skip commit and report
                if receipt.verdict != "PASS":
                    raise ValueError(f"AUDIT_GATE blocked ch.{target_ch}: verdict={receipt.verdict}, issues={[r.reason for r in receipt.check_results[:2]]}")
                self.engine.tx_mgr.commit_transaction(target_ch, draft, outline, state_delta, expected_hash=self.state_mgr.calculate_draft_hash(draft.content), audit_receipt=receipt)
                
                self.current_task.completed_chapters += 1
                success_msg = f"✅ Chương {target_ch}: '{draft.title}' hoàn tất thành công! ({draft.word_count} chữ, OOC Score: {critique.ooc_score}/10)"
                self.current_task.logs.append(success_msg)
                if listener:
                    listener({"type": "chapter_completed", "message": success_msg, "chapter": target_ch, "draft": draft.model_dump()})

            except Exception as e:
                err_msg = f"❌ Lỗi tại Chương {target_ch}: {str(e)}"
                self.current_task.logs.append(err_msg)
                self.current_task.status = "failed"
                if listener:
                    listener({"type": "error", "message": err_msg})
                break

        if self.current_task.completed_chapters == count:
            self.current_task.status = "completed"
        self.current_task.end_time = time.time()
        self.is_running = False
        return self.current_task
