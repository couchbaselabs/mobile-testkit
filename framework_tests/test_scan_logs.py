import pytest

from utilities import scan_logs


def test_panic_in_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "framework_tests/test_data/mock_panic_log.txt"

    with pytest.raises(AssertionError) as e:
        scan_logs.scan_for_errors(['panic'], log_file_path)

    error_message = str(e.value)
    assert error_message.startswith("panic found!!")


def test_warning_in_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "framework_tests/test_data/mock_panic_log.txt"

    with pytest.raises(AssertionError) as e:
        scan_logs.scan_for_errors(['warning'], log_file_path)

    error_message = str(e.value)
    assert error_message.startswith("warning found!!")


def test_cap_warning_in_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "framework_tests/test_data/mock_panic_log.txt"

    with pytest.raises(AssertionError) as e:
        scan_logs.scan_for_errors(['warning'], log_file_path)

    error_message = str(e.value)
    assert error_message.startswith("warning found!!")


def test_cap_panic_in_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "framework_tests/test_data/mock_panic_log.txt"

    with pytest.raises(AssertionError) as e:
        scan_logs.scan_for_errors(['Panic'], log_file_path)

    error_message = str(e.value)
    assert error_message.startswith("Panic found!!")


def test_clean_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "framework_tests/test_data/mock_clean_log.txt"

    scan_logs.scan_for_errors(['panic'], log_file_path)

