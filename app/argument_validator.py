import re
from app.schemas import ActionProposal

class Validation_result:

    def __init__(self, valid: bool, reason : str):
        self.valid = valid
        self.reason = reason


class ArgumentValidator:

    max_transfer_amount = 100000

    def validate(self, proposal : ActionProposal) -> Validation_result:

        if proposal.action == "send_email":
            return self._validate_email(proposal)
        
        if proposal.action == "delete_file":
            return self._validate_file(proposal)

        if proposal.action == "transfer_money":
            return self._validate_transfer(proposal)

        if proposal.action == "search_web":
            return self._validate_web(proposal)

        if proposal.action == "unstable_tool":
            return Validation_result(
                valid = True,
                reason = "Unstable tool is valid for testing."
            )

        return Validation_result(
            valid = False,
            reason = "Unknown action"
        )

    def _validate_email(self, proposal: ActionProposal) -> Validation_result:

        if not proposal.target:
            return Validation_result(
                valid = False,
                reason = "Email is Empty."
            )

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(pattern, proposal.target):
            return Validation_result(
                valid = False,
                reason = "Email is not correct."
            )
        
        return Validation_result(
            valid = True,
            reason = "Email is correct."
        )

    def _validation_search(self, proposal: ActionProposal) -> Validation_result:

        if not proposal.target:
            return Validation_result(
                valid = False,
                reason = "Search is empty."
            )

        if (proposal.target.strip()) < 2:
            return Validation_result(
                valid = False,
                reason = "Query is short to search."
            )

        return Validation_result(
            valid = True,
            reason = "Query is good for search."
        )

    def _validate_file(self, proposal : ActionProposal) -> Validation_result:

        if not proposal.target:
            return Validation_result(
                valid = False,
                reason = "There is no file."
            )
        
        dangerous_patterns = [
            "..",
            "/etc/",
            "/system/",
            "windows/system32",
            "passwd"
        ]

        for pattern in dangerous_patterns:

            if pattern in proposal.target:
                return Validation_result(
                    valid = False,
                    reason = "No such path exists."
                )

        return Validation_result(
            valid = True,
            reason = "File path is good."
        )

    def _validate_transfer(self, proposal : ActionProposal) -> Validation_result:

        if not proposal.target:
            return Validation_result(
                valid = False,
                reason = "Amount is missing."
            )
        
        if proposal.target is None:
            return Validation_result(
                valid = False,
                reason = "Amount is missing."
            )

        if proposal.target <= 0:
            return Validation_result(
                valid = False,
                reason = "Amount must be greater than 0."
            )

        if proposal.target > self.max_transfer_amount:
            return Validation_result(
                valid = False,
                reason = "Amount is too large."
            )
        
        return Validation_result(
            valid = True,
            reason = "Amount is good."
        )




    