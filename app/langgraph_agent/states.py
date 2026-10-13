from typing import TypedDict, Optional, Any
from app.schemas import ActionProposal

class AgentState(TypedDict, total = False):
    user_request : str
    proposal : Optional[ActionProposal]
    governance_decision : Optional[str]
    execution_result : Optional[dict[str, Any]]
    status : str
    audit_log : list[str]


    



