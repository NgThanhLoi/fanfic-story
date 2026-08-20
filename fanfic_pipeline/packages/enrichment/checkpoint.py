"""
Enrichment Checkpoint: Persists extraction progress per batch window, enabling seamless resume after interruption.
"""
import json, pathlib, os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class EnrichmentCheckpoint(BaseModel):
    project_id: str = "nhat_the_fanfic"
    total_chapters: int = 1409
    window_size: int = 30
    completed_windows: List[int] = Field(default_factory=list)
    last_completed_chapter: int = 0
    stats: Dict[str, int] = Field(default_factory=dict)
    updated_at: str = ""

    def is_window_completed(self, window_id: int) -> bool:
        return window_id in self.completed_windows

    def mark_window_completed(self, window_id: int, end_chapter: int, current_stats: Optional[Dict[str, int]] = None):
        if window_id not in self.completed_windows:
            self.completed_windows.append(window_id)
        self.last_completed_chapter = max(self.last_completed_chapter, end_chapter)
        if current_stats:
            self.stats = current_stats
        self.updated_at = datetime.now().isoformat()

    def save(self, path: str):
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(path).write_text(json.dumps(self.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "EnrichmentCheckpoint":
        if not os.path.exists(path):
            return cls()
        return cls(**json.loads(pathlib.Path(path).read_text(encoding="utf-8")))
