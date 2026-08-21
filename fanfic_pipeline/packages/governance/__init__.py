"""Governance package — production governance layer (spec 2026-08-21 §1)."""
from fanfic_pipeline.packages.governance.policy import RuntimePolicy, DEFAULT_POLICY
from fanfic_pipeline.packages.governance.topology import (
    TransitionTopology,
    TopologyViolation,
    load_default_topology,
    normalize_vi,
)
from fanfic_pipeline.packages.governance.premise import PremiseValidator, PremiseReceipt
from fanfic_pipeline.packages.governance.readiness import ReadinessGate, ReadinessResult
from fanfic_pipeline.packages.governance.compliance import (
    ComplianceReport,
    SubsystemStatus,
    derive_chapter_numbers,
    evidence_hash,
    SUBSYSTEMS,
)

__all__ = [
    "RuntimePolicy", "DEFAULT_POLICY",
    "TransitionTopology", "TopologyViolation", "load_default_topology", "normalize_vi",
    "PremiseValidator", "PremiseReceipt",
    "ReadinessGate", "ReadinessResult",
    "ComplianceReport", "SubsystemStatus", "derive_chapter_numbers", "evidence_hash",
    "SUBSYSTEMS",
]
