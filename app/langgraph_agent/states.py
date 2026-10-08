from typing import TypedDict, Optional
from app.schemas import ActionProposal

class AgentState(TypedDict, total = False):
    user_request : str
    proposal : Optional[ActionProposal]
    execution_result : Optional[str]
    status : str



