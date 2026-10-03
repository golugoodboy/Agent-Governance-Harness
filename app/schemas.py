from enum import Enum
from pydantic import BaseModel, Field

class Decision(str, Enum):
    ALLOW = "ALLOW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK = "BLOCK"

class ActionProposal(BaseModel):
    action : str
    reason : str
    confidence: float = Field(le = 1.0, ge = 0.0)
    risk_level : str
    target : str | None = None


class GovernorDecision(BaseModel):
    decision : Decision
    reason : str
    risk_score : float = Field(le = 1.0, ge = 0.0)

