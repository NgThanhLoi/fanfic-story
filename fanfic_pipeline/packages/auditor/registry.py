"""
Checker Registry: Auto-discovery and lookup for all audit checkers.
"""
from typing import Dict, List, Type
from fanfic_pipeline.packages.auditor.base import BaseChecker
from fanfic_pipeline.packages.auditor.checkers.word_count import WordCountChecker
from fanfic_pipeline.packages.auditor.checkers.alive_dead import AliveDeadChecker
from fanfic_pipeline.packages.auditor.checkers.hash_branch import HashBranchChecker
from fanfic_pipeline.packages.auditor.checkers.realm_strictness import RealmStrictnessChecker
from fanfic_pipeline.packages.auditor.checkers.resource_ledger import ResourceLedgerChecker
from fanfic_pipeline.packages.auditor.checkers.spatial_continuity import SpatialContinuityChecker
from fanfic_pipeline.packages.auditor.checkers.timeline_consistency import TimelineConsistencyChecker
from fanfic_pipeline.packages.auditor.checkers.frozen_canon import FrozenCanonChecker
from fanfic_pipeline.packages.auditor.checkers.ai_pattern import AIPatternChecker
from fanfic_pipeline.packages.auditor.checkers.pod_compatibility import PODCompatibilityChecker
from fanfic_pipeline.packages.auditor.checkers.canon_orphan import CanonOrphanChecker
from fanfic_pipeline.packages.auditor.checkers.butterfly_debt import ButterflyDebtChecker
from fanfic_pipeline.packages.auditor.checkers.divergence_monotonicity import DivergenceMonotonicityChecker
from fanfic_pipeline.packages.auditor.checkers.ooc_fidelity import OOCFidelityChecker
from fanfic_pipeline.packages.auditor.checkers.relationship_dynamics import RelationshipDynamicsChecker
from fanfic_pipeline.packages.auditor.checkers.pacing import PacingChecker
from fanfic_pipeline.packages.auditor.checkers.canon_fidelity import CanonFidelityChecker
from fanfic_pipeline.packages.auditor.checkers.epistemic_claim import EpistemicClaimChecker
from fanfic_pipeline.packages.auditor.checkers.meta_leak import MetaLeakChecker
from fanfic_pipeline.packages.auditor.checkers.transition_topology import TransitionTopologyChecker
from fanfic_pipeline.packages.auditor.checkers.domain_fill import DomainFillChecker
from fanfic_pipeline.packages.auditor.checkers.style_fingerprint import StyleFingerprintChecker
from fanfic_pipeline.packages.auditor.checkers.identity_reveal import IdentityRevealChecker
from fanfic_pipeline.packages.auditor.checkers.bounded_progression import BoundedProgressionChecker
from fanfic_pipeline.packages.auditor.checkers.combat_style import CombatStyleChecker
from fanfic_pipeline.packages.auditor.checkers.sensory_density import SensoryDensityChecker

DEFAULT_CHECKERS: List[Type[BaseChecker]] = [
    WordCountChecker, AliveDeadChecker, HashBranchChecker, RealmStrictnessChecker,
    ResourceLedgerChecker, SpatialContinuityChecker, TimelineConsistencyChecker,
    FrozenCanonChecker, AIPatternChecker, PODCompatibilityChecker, CanonOrphanChecker,
    ButterflyDebtChecker, DivergenceMonotonicityChecker, OOCFidelityChecker,
    RelationshipDynamicsChecker, PacingChecker, CanonFidelityChecker,
    EpistemicClaimChecker, MetaLeakChecker, TransitionTopologyChecker, DomainFillChecker,
    StyleFingerprintChecker, IdentityRevealChecker, BoundedProgressionChecker,
    CombatStyleChecker, SensoryDensityChecker
]

class CheckerRegistry:
    def __init__(self):
        self._checkers: Dict[str, BaseChecker] = {}
        for cls in DEFAULT_CHECKERS:
            instance = cls()
            self._checkers[instance.checker_id] = instance

    def get(self, checker_id: str) -> BaseChecker:
        return self._checkers.get(checker_id)

    def list_checkers(self) -> List[BaseChecker]:
        return list(self._checkers.values())

    def register(self, checker: BaseChecker):
        self._checkers[checker.checker_id] = checker
