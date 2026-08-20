"""
P2.4 — Counterfactual (incremental recompute + cache)
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field
import json, pathlib

class CounterfactualCache(BaseModel):
    computed_from: Dict[str,Any] = Field(default_factory=dict)
    events: Dict[str, Any] = Field(default_factory=dict)  # event_id -> {status, reason, depth}
    stats: Dict[str, int] = Field(default_factory=dict)
    drift_since_full: float = 0.0

    def status_of(self, event_id: str) -> str:
        return self.events.get(event_id, {}).get("status", "intact")

    def cannot_happen(self) -> List[str]:
        return [eid for eid, v in self.events.items() if v.get("status")=="cannot_happen"]

    def stats_summary(self) -> Dict[str,int]:
        s={"cannot_happen":0,"altered":0,"weakened":0,"intact":0}
        for v in self.events.values():
            st=v.get("status","intact")
            if st in s: s[st]+=1
        return s

    def update_from_status(self, status_dict: Dict[str, Any]):
        for eid, st in status_dict.items():
            st_val = st.status if hasattr(st, "status") else st.get("status", "intact")
            depth_val = st.depth if hasattr(st, "depth") else st.get("depth", 0)
            self.events[eid] = {"status": st_val, "depth": depth_val}
        self.stats = self.stats_summary()

    def save(self, path: str):

        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(path).write_text(json.dumps(self.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "CounterfactualCache":
        return cls(**json.loads(pathlib.Path(path).read_text(encoding="utf-8")))
