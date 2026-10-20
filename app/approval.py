import hashlib
import json

from app.schemas import ActionProposal


def proposal_fingerprint(proposal: ActionProposal) -> str:
    """
    Create a deterministic SHA-256 fingerprint for an action proposal.

    The same proposal produces the same fingerprint.
    Changing any proposal field produces a different fingerprint.
    """
    payload = proposal.model_dump(mode="json")

    canonical_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()
