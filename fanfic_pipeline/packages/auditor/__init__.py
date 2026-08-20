"""
Auditor Package: Modular Fail-Closed Audit System for Fanfic Pipeline.
"""
from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext
from fanfic_pipeline.packages.auditor.registry import CheckerRegistry
from fanfic_pipeline.packages.auditor.runner import AuditRunner
from fanfic_pipeline.packages.auditor.receipt import AuditReceipt, DimensionResult

__all__ = [
    "BaseChecker",
    "CheckResult",
    "AuditContext",
    "CheckerRegistry",
    "AuditRunner",
    "AuditReceipt",
    "DimensionResult"
]
