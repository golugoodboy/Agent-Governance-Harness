import operator
from typing import TypedDict, Optional, Any, Annotated
from app.schemas import ActionProposal

class AgentState(TypedDict, total = False):
    user_request : str
    audit_run_id: str
    proposal : Optional[ActionProposal]
    governance_decision : Optional[str]
    execution_result : Optional[dict[str, Any]]
    status : str
    audit_log : Annotated[list[str], operator.add]

    step_count : int
    max_steps : int
    final_response : str
    next_step : str

    approval_status : str










