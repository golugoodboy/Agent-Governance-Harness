from app.schemas import ActionProposal, GovernorDecision, Decision
from app.risk_engine import RiskEngine 

class Governor:

    def __init__(self):
        self.risk_engine = RiskEngine()

    def evaluate(self, proposal : ActionProposal) -> GovernorDecision:

        risk_score = self.risk_engine.calculate(proposal)

        if risk_score >= 0.80:
            return GovernorDecision(
                decision = Decision.HUMAN_REVIEW,
                reason = "High Risk Detected",
                risk_score = risk_score
            )

        if risk_score >= 0.60:
            return GovernorDecision(
                decision = Decision.HUMAN_REVIEW,
                reason = "Moderate Risk Detected",
                risk_score = risk_score
            )
        
        if proposal.confidence < 0.50:
            return GovernorDecision(
                decision = Decision.HUMAN_REVIEW,
                reason = "Low confidence",
                risk_score = risk_score
            )

        return GovernorDecision(
            decision = Decision.ALLOW,
            reason = "Low Risk and high confidence",
            risk_score = risk_score
        )
