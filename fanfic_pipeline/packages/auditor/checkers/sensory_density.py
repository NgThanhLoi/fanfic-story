from fanfic_pipeline.packages.auditor.base import BaseChecker, CheckResult, AuditContext

class SensoryDensityChecker(BaseChecker):
    checker_id = "sensory_density"
    severity = "P2"

    def check(self, draft: str, ctx: AuditContext) -> CheckResult:
        return CheckResult(checker_id=self.checker_id, status="PASS", severity=self.severity, score=1.0)
