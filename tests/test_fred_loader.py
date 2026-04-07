from loaders.fred_loader import _is_non_retryable_fred_error


def test_is_non_retryable_fred_error_for_missing_series():
    error = Exception("Bad Request. The series does not exist.")
    assert _is_non_retryable_fred_error(error) is True


def test_is_non_retryable_fred_error_for_transient_failure():
    error = Exception("Connection timed out")
    assert _is_non_retryable_fred_error(error) is False
