"""
P1.11 — Master KnowledgePackLoader: Unified, O(1) in-memory loader for Fandom Master Lore Packs.
"""
import os, json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class CanonKnowledgePack(BaseModel):
    fandom_id: str
    manifest: Dict[str, Any]
    world_geography: Dict[str, Any]
    cosmic_invariants: Dict[str, Any]
    cultivation_mechanics: Dict[str, Any]
    factions_and_conspiracies: Dict[str, Any]
    canonical_timeline: Dict[str, Any]
    character_dossiers: Dict[str, Any]

class KnowledgePackLoader:
    _CACHE: Dict[str, CanonKnowledgePack] = {}

    @classmethod
    def load(cls, fandom_id: str = "nhat_the_chi_ton") -> CanonKnowledgePack:
        if fandom_id in cls._CACHE:
            return cls._CACHE[fandom_id]
        
        base_dir = os.path.join(os.path.dirname(__file__), fandom_id)
        if not os.path.exists(base_dir):
            base_dir = os.path.join(os.path.dirname(__file__), "nhat_the_chi_ton")

        def _read_json(fname: str) -> Dict[str, Any]:
            p = os.path.join(base_dir, fname)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}

        pack = CanonKnowledgePack(
            fandom_id=fandom_id,
            manifest=_read_json("manifest.json"),
            world_geography=_read_json("world_geography.json"),
            cosmic_invariants=_read_json("cosmic_invariants.json"),
            cultivation_mechanics=_read_json("cultivation_mechanics.json"),
            factions_and_conspiracies=_read_json("factions_and_conspiracies.json"),
            canonical_timeline=_read_json("canonical_timeline.json"),
            character_dossiers=_read_json("character_dossiers.json")
        )
        cls._CACHE[fandom_id] = pack
        return pack
