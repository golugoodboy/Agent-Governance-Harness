from app.schemas import ActionProposal, GovernorDecision, Decision

class Governor:

    def evaluate(self, proposal : ActionProposal) -> GovernorDecision:

        # Rule 1 : Very low confidence
        if proposal.confidence < 0.50:
            return GovernorDecision(
                decision = Decision.HUMAN_REVIEW,
                reason = "AI confidnece is too low",
                risk_score = 0.80
            )

        #Rule 2 : Dangerous Action
        dangerous_actions = {"delete_file", "delete_database", "transfer_money"}

        if proposal.action in dangerous_actions:
            return GovernorDecision(
                decision = Decision.HUMAN_REVIEW,
                reason = "Dangerous action detected",
                risk_score = 0.90
            )

        
        #Rule 3: Explicit High Risk
        if proposal.risk_level.lower() == "high":
            return GovernorDecision(
                decision = Decision.HUMAN_REVIEW,
                reason = "High risk action explicitly flagged",
                risk_score = 0.95
            )

        return GovernorDecision(
            decision = Decision.ALLOW,
            reason = "AI passed all the safety checks.",
            risk_score = 0.20
        )

