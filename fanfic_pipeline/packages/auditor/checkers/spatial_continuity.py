from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class SpatialContinuityChecker(BaseChecker):
    checker_id = "spatial_continuity"
    severity = "P0"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
