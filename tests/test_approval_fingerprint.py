
from app.approval import proposal_fingerprint
from app.schemas import ActionProposal


def make_proposal(target="alice@example.com"):
    return ActionProposal(
        action="send_email",
        reason="Send a test email",
        confidence=0.95,
        risk_level="medium",
        target=target,
    )


def test_same_proposal_has_same_fingerprint():
    proposal = make_proposal()

    assert proposal_fingerprint(proposal) == proposal_fingerprint(proposal)


def test_changed_target_has_different_fingerprint():
    proposal_a = make_proposal("alice@example.com")
    proposal_b = make_proposal("attacker@example.com")

    assert proposal_fingerprint(proposal_a) != proposal_fingerprint(proposal_b)


def test_changed_confidence_has_different_fingerprint():
    proposal_a = make_proposal()
    proposal_b = proposal_a.model_copy(update={"confidence": 0.60})

    assert proposal_fingerprint(proposal_a) != proposal_fingerprint(proposal_b)
