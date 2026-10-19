from unittest.mock import patch

from app.governor import Governor
from app.schemas import ActionProposal, Decision
from app.permission import Permission


def test_permission_denial_overrides_high_risk():
    proposal = ActionProposal(
        action="transfer_money",
        reason="Security regression test",
        confidence=0.99,
        risk_level="high",
        target="test_account",
        amount=1000,
    )

    governor = Governor()

    with (
        patch.object(
            governor.risk_engine,
            "calculate",
            return_value=0.95,
        ),
        patch.object(
            governor.permission_engine,
            "check",
            return_value=Permission.DENY,
        ),
        patch.object(
            governor.validator,
            "validate",
        ) as validate,
    ):
        decision = governor.evaluate(proposal)

    assert decision.decision == Decision.BLOCK
    validate.assert_not_called()
