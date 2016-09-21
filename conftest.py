import pytest

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Setup hooks to detect test outcome status in all test fixtures.

    This allows conditional actions based upon the result. (i.e. pull logs only on failure, etc)
    Implementation from: http://doc.pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
    """

    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set an report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)
