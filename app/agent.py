from app.schemas import ActionProposal


def simulate_agent(request : str) -> ActionProposal:

    if "transfer" in request.lower():
        return ActionProposal(
            action = "transfer money",
            reason = "urgent payment needed",
            confidence = 0.62,
            risk_level = "medium",
            target = "account no. ........",
            amount = 5000.0
        )

    if "delete" in request.lower():
        return ActionProposal(
            action = "delete file",
            reason = "user requested deletion",
            confidence = 0.92,
            risk_level = "high",
            target = "important_file.txt"
        )

    if "email" in request.lower():
        return ActionProposal(
            action = "send email",
            reason = "user requested to send email",
            confidence = 0.85,
            risk_level = "medium",
            target = "customer@gmail.com"
        )

    return ActionProposal(
        action = "search web",
        reason = "general knowledge query",
        confidence = 0.90,
        risk_level = "low"
    )

