import pytest
from keywords.exceptions import LogScanningError

from utilities import scan_logs


def test_error_string_not_list():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "mobile_testkit_tests/test_data/mock_panic_log.txt"

    with pytest.raises(ValueError) as e:
        scan_logs.scan_for_errors(log_file_path, 'panic')

    error_message = str(e.value)
    assert error_message.startswith("error_strings must be a list")


def test_panic_in_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "mobile_testkit_tests/test_data/mock_panic_log.txt"

    with pytest.raises(LogScanningError) as e:
        scan_logs.scan_for_errors(log_file_path, ['panic'])

    error_message = str(e.value)
    assert error_message.startswith("panic found!!")


def test_warning_in_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "mobile_testkit_tests/test_data/mock_panic_log.txt"

    with pytest.raises(LogScanningError) as e:
        scan_logs.scan_for_errors(log_file_path, ['warning'])

    error_message = str(e.value)
    assert error_message.startswith("warning found!!")


def test_cap_warning_in_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "mobile_testkit_tests/test_data/mock_panic_log.txt"

    with pytest.raises(LogScanningError) as e:
        scan_logs.scan_for_errors(log_file_path, ['warning'])

    error_message = str(e.value)
    assert error_message.startswith("warning found!!")


def test_cap_panic_in_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "mobile_testkit_tests/test_data/mock_panic_log.txt"

    with pytest.raises(LogScanningError) as e:
        scan_logs.scan_for_errors(log_file_path, ['Panic'])

    error_message = str(e.value)
    assert error_message.startswith("Panic found!!")


def test_clean_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "mobile_testkit_tests/test_data/mock_clean_log.txt"

    scan_logs.scan_for_errors(log_file_path, ['panic'])
    scan_logs.scan_for_errors(log_file_path, ['data race'])


def test_data_race_log():
    """
    Make sure scanner throws exception for found keyword
    """

    log_file_path = "mobile_testkit_tests/test_data/mock_data_race_log.txt"

    with pytest.raises(LogScanningError) as e:
        scan_logs.scan_for_errors(log_file_path, ['data race'])

    error_message = str(e.value)
    assert error_message.startswith("data race found!!")

    with pytest.raises(LogScanningError) as e:
        scan_logs.scan_for_errors(log_file_path, ['DATA RACE'])

    error_message = str(e.value)
    assert error_message.startswith("DATA RACE found!!")
