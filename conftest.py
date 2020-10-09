import pytest
from utilities.xml_parser import custom_rerun_xml_merge, merge_reports


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


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    if session.config.getoption("--merge"):
        paths = session.config.getoption("--merge")
        merge_reports(paths)
    if session.config.getoption("--rerun-tests"):
        rerun_result_option = session.config.getoption("--rerun-tests")
        result_option = rerun_result_option
        result_option = result_option.split("=")
        custom_rerun_xml_merge(result_option[1], result_option[0])


def pytest_addoption(parser):
    parser.addoption("--merge", action="store",
                     help="Merge the report files path pattern, like results/**.xml. e.g.  -m '["
                          "results/***.xml]'",
                     default="")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    print("Starting the tests .....")

