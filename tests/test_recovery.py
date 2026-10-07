from app.recovery_manager import RecoveryManager, RecoveryAction


def test_retryable_error():

    manager = RecoveryManager()

    result = manager.decide(
        error="timeout",
        attempt=1
    )

    assert result == RecoveryAction.RETRY


def test_non_retryable_error():

    manager = RecoveryManager()

    result = manager.decide(
        error="invalid email",
        attempt=1
    )

    assert result == RecoveryAction.STOP


def test_max_retries():

    manager = RecoveryManager()

    result = manager.decide(
        error="timeout",
        attempt=3
    )

    assert result == RecoveryAction.FAIL