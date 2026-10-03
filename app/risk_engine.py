class RiskEngine:

    ACTION_RISK = {
        "delete_file" : 0.90,
        "transfer_money" : 0.95,
        "send_email" : 0.30,
        "search_web" : 0.10
    }

    def calculate(self, proposal):
        action_risk = self.ACTION_RISK.get(proposal.action, 0.50)

        confidence = 1 - proposal.confidence

        explicit_risk = {
            "low" : 0.10,
            "medium" : 0.40,
            "high" : 0.70
        }.get(proposal.risk_level.lower(), 0.50)

        risk_score = (action_risk * 0.5) + (confidence * 0.3) + (explicit_risk * 0.2)

        return round(risk_score, 3)


