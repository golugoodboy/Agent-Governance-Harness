from app.schemas import ActionProposal, GovernorDecision, Decision
from app.tools import *
from app.governor import Governor
from app.tool_normalizer import normalize_toolname
from app.tool_registry import TOOLS

class Executor:
    def __init__(self):
        self.governor = Governor()
        self.tools = {
            "search_web" : search_web,
            "send_email" : send_email,
            "delete_file" : delete_file,
            "transfer_money" : transfer_money
        }

    def execute(self, proposal : ActionProposal):
        
        canonical_action = normalize_toolname(proposal.action)

        proposal.action = canonical_action

        decision = self.governor.evaluate(proposal)

        print("\n Governor Decision")
        print(decision)

        if decision.decision != Decision.ALLOW:
            return {
                "status" : "blocked",
                "decision" : decision.decision,
                "reason" : decision.reason
            }

        tool = TOOLS.get(proposal.action)

        if tool is None: 
            return 
            {
                "status" : "blocked",
                "reason" : "unknown tool"
            }

        if proposal.action == "search_web":
            return tool(proposal.target)

        if proposal.action == "send_email":
            return tool(proposal.target)

        if proposal.action == "delete_file":
            return tool(proposal.target)

        if proposal.action == "transfer_money":
            return tool(proposal.target, proposal.amount)

        if "unknown" in request.lower():
            return ActionProposal(
                action="teleport_customer",
                reason="Testing unknown tool handling.",
                confidence=0.99,
                risk_level="low"
            )

    