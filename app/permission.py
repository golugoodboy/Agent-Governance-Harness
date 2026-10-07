from enum import Enum
from app.schemas import ActionProposal

class Permission(str, Enum):
    ALLOW = "ALLOW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    DENY = "DENY"


class PermissionEngine:

    tool_policies = {
        "delete_file" : Permission.HUMAN_REVIEW,
        "transfer_money" : Permission.DENY,
        "search_web" : Permission.ALLOW,
        "send_email" : Permission.ALLOW,
        "unstable_tool" : Permission.ALLOW
    }

    def check(self, proposal : ActionProposal) -> Permission:
        permission = self.tool_policies.get(proposal.action, Permission.DENY)
        print(f"[HARNESS] Action {proposal.action} has permission = {permission}")
        return permission




