from enum import Enum

class RecoveryAction(Enum):
    RETRY = "RETRY"
    FAIL = "FAIL"
    STOP = "STOP"


class RecoveryManager:

    max_tries = 3

    def decide(self, error : str, attempt : int) -> RecoveryAction:

        error_lower = error.lower()

        RETRYABLE_ERRORS = {
            "timeout",
            "network_error",
            "service_unavailable",
            "temporary_error"
        }

        if attempt >= self.max_tries:
            return RecoveryAction.FAIL

        for error_type in RETRYABLE_ERRORS:
            if error_type in error_lower:
                return RecoveryAction.RETRY

        return RecoveryAction.STOP

