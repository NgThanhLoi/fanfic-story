"""
Fanfic Studio - Web UI Interface (v1.0 Production Architecture):
Runs locally to provide an interactive visual workspace for Long-Form Fanfic creation.
"""

import os
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from fanfic_pipeline.core.state_manager import ProjectStateManager
from fanfic_pipeline.core.engine import FanficEngine
from fanfic_pipeline.core.models import PointOfDivergence, RelationshipState, ChapterDraft, ChapterOutline
from fanfic_pipeline.core.story_state import StoryStateManager, StateDelta
from fanfic_pipeline.data.nhat_the_chi_ton.knowledge import CHARACTER_VOICES, REALMS, LUC_DAO_RULES

app = FastAPI(title="Fanfic AI Studio v1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = os.environ.get("FANFIC_PROJECT_ID", "nhat_the_fanfic")
state_mgr = ProjectStateManager(PROJECT_ID)

if not os.path.exists(state_mgr.meta_path):
    pod = PointOfDivergence(
        divergence_anchor="Nhiệm vụ Luân Hồi tân thủ Ẩn Hình phường",
        what_if_premise="Mạnh Kỳ phát giác dấu vết Ma Phật An Nan và nhận ra chân tướng Lục Đạo sớm hơn",
        butterfly_effects=[
            "Cố Tiểu Tang nhận ra sự dị thường nên tiếp cận và trêu chọc Mạnh Kỳ sớm hơn",
            "Tiểu đội Luân Hồi gắn kết chặt chẽ và chuẩn bị kỹ lưỡng hơn cho các trận chiến sinh tử"
        ],
        frozen_canon=[
            "Hệ thống cảnh giới Khai Khiếu -> Ngoại Cảnh -> Pháp Thân giữ nguyên",
            "Quy tắc xóa sổ và trừ thiện công của Lục Đạo giữ nguyên"
        ]
    )
    relationships = [
        RelationshipState(
            pair=["Mạnh Kỳ", "Cố Tiểu Tang"],
            trope_type="Enemies to Lovers / Mind Games & Mutual Pining",
            intimacy_level=2,
            current_dynamic="Thăm dò lẫn nhau, vừa cảnh giác vừa bị cuốn hút",
            unspoken_conflicts=["Thân phận Ma Môn và sự khống chế của Vô Sinh Lão Mẫu"]
        ),
        RelationshipState(
            pair=["Mạnh Kỳ", "Giang Chỉ Vi"],
            trope_type="Comrades in Arms / Sword Kinship",
            intimacy_level=5,
            current_dynamic="Đồng đội sinh tử chi giao, tin tưởng tuyệt đối vào nhân phẩm và kiếm đạo",
            unspoken_conflicts=[]
        )
    ]
    state_mgr.init_project(
        title="Nhất Thế Chi Tôn: Đao Kiếm Tương Phùng",
        fandom="Nhất Thế Chi Tôn (一世之尊)",
        pod=pod,
        voices=CHARACTER_VOICES,
        relationships=relationships,
        execution_mode="HUMAN_IN_THE_LOOP"
    )

engine = FanficEngine(state_mgr)

class ChapterPlanRequest(BaseModel):
    author_instruction: str = ""
    target_chapter: Optional[int] = None

class ChapterCommitRequest(BaseModel):
    chapter_number: int
    title: str
    content: str
    summary: str
    outline_data: Dict[str, Any]

@app.get("/api/status")
def get_status():
    meta = state_mgr.load_project_meta()
    pod = state_mgr.load_pod().model_dump()
    voices = {k: v.model_dump() for k, v in state_mgr.load_voices().items()}
    relationships = [r.model_dump() for r in state_mgr.load_relationships()]
    state = state_mgr.load_story_state()
    recent = state_mgr.get_recent_summaries(limit=5)
    
    return {
        "meta": meta,
        "pod": pod,
        "voices": voices,
        "relationships": relationships,
        "state": state,
        "recent_chapters": recent,
        "realms": REALMS,
        "luc_dao_rules": LUC_DAO_RULES
    }

@app.post("/api/plan-chapter")
def plan_chapter(req: ChapterPlanRequest):
    meta = state_mgr.load_project_meta()
    next_ch = req.target_chapter or (meta.get("current_chapter", 0) + 1)
    outline = engine.plan_chapter(next_ch, req.author_instruction)
    return outline.model_dump()

@app.post("/api/draft-chapter")
def draft_chapter(req: Dict[str, Any]):
    outline_data = req.get("outline")
    outline = ChapterOutline(**outline_data)
    draft = engine.write_draft(outline)
    critique = engine.audit_draft(outline, draft)
    return {
        "draft": draft.model_dump(),
        "critique": critique.model_dump()
    }

@app.post("/api/commit-chapter")
def commit_chapter(req: ChapterCommitRequest):
    draft = ChapterDraft(
        chapter_number=req.chapter_number,
        title=req.title,
        word_count=len(req.content.split()),
        content=req.content,
        summary=req.summary
    )
    outline = ChapterOutline(**req.outline_data)
    current_state = state_mgr.load_story_state()
    delta = StoryStateManager.extract_state_delta(req.chapter_number, req.content, current_state)
    
    draft_hash = state_mgr.calculate_draft_hash(req.content)
    # v1.1 fail-closed: require PASS audit receipt
    from fanfic_pipeline.packages.auditor.matrix_33 import ConsistencyVerificationStack
    receipt = ConsistencyVerificationStack.evaluate("", req.content, req.outline_data, audited_hash=draft_hash)
    if receipt.verdict != "PASS":
        return {"status": "blocked", "verdict": receipt.verdict, "issues": receipt.issues, "checker_results": [r.model_dump() for r in receipt.checker_results]}
    result = engine.tx_mgr.commit_transaction(
        req.chapter_number, draft, outline, state_delta=delta, expected_hash=draft_hash, audit_receipt=receipt
    )
    return {"status": "success", "chapter_number": req.chapter_number, "tx": result}

@app.get("/", response_class=HTMLResponse)
def index_page():
    # Read embedded UI
    html_file = Path(__file__).resolve().parent / "ui" / "index.html"
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    
    # Fallback minimal HTML
    return """
    <!DOCTYPE html><html><head><title>Fanfic AI Studio v1.0</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-950 text-slate-100 p-8">
        <h1 class="text-2xl font-bold text-cyan-400">Fanfic AI Studio v1.0 (Production Target)</h1>
        <p class="text-slate-400 mt-2">API endpoints active at /api/status, /api/plan-chapter, /api/draft-chapter, /api/commit-chapter</p>
    </body></html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
