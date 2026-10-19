from app.schemas import ActionProposal, GovernorDecision, Decision
from app.risk_engine import RiskEngine 
from app.permission import PermissionEngine, Permission
from app.argument_validator import ArgumentValidator
from app.tool_normalizer import ToolNormalizer

class Governor:

    def __init__(self):
        self.risk_engine = RiskEngine()
        self.permission_engine = PermissionEngine()
        self.validator = ArgumentValidator()
        self.tool_normalizer = ToolNormalizer()
    def evaluate(self, proposal : ActionProposal, human_approved: bool = False) -> GovernorDecision:

        proposal = proposal.model_copy(
            update = {
                "action" : self.tool_normalizer.normalize(proposal.action)
                },
                
        )
        
        risk_score = self.risk_engine.calculate(proposal)

        # tool permission check (permission denial overrides risk evaluation)
        permission = self.permission_engine.check(proposal)

        if permission == Permission.DENY:
            return GovernorDecision(
                decision=Decision.BLOCK,
                reason=f"Tool {proposal.action} is not authorized.",
                risk_score=risk_score
            )
        
        if permission == Permission.HUMAN_REVIEW:
            return GovernorDecision(
                decision=Decision.HUMAN_REVIEW,
                reason=f"Tool {proposal.action} needs human approval.",
                risk_score=risk_score
            )

        print(f"[HARNESS] permission={permission}")

        if risk_score >= 0.80:
            return GovernorDecision(
                decision=Decision.HUMAN_REVIEW,
                reason="High Risk Detected",
                risk_score=risk_score
            )

        if risk_score >= 0.60:
            return GovernorDecision(
                decision=Decision.HUMAN_REVIEW,
                reason="Moderate Risk Detected",
                risk_score=risk_score
            )
        
        if proposal.confidence < 0.50 and not human_approved:
            return GovernorDecision(
                decision=Decision.HUMAN_REVIEW,
                reason="Low confidence",
                risk_score=risk_score
            )

        print(
            f"[HARNESS] action={proposal.action} "
            f"risk={risk_score}"
        )



        #validator 

        validation = self.validator.validate(proposal)

        print(
            f"Harness Validation :{validation.valid}, "
            f"Reason: {validation.reason}"
        )

        if not validation.valid:
            return GovernorDecision(
                decision = Decision.BLOCK,
                reason = validation.reason,
                risk_score = risk_score
            )

        return GovernorDecision(
            decision = Decision.ALLOW,
            reason = "Approved by human after safety checks" if human_approved else "Authorized, validated, and low risk",
            risk_score = risk_score
        )



