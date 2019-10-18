# content of conftest.py

import pytest


# @pytest.hookimpl(tryfirst=True, hookwrapper=True)
# def pytest_runtest_makereport(item, call):
#     # execute all other hooks to obtain the report object
#     outcome = yield
#     rep = outcome.get_result()
# 
#     # set a report attribute for each phase of a call, which can
#     # be "setup", "call", "teardown"
# 
#     setattr(item, "rep_" + rep.when, rep)

@pytest.fixture(scope="session")
def nothing(request):
    print "In session\n"
    yield
    # request.node is an "item" because we use the default
    # "function" scope
#     if request.node.rep_setup.failed:
#         print("setting up a test failed!", request.node.nodeid)
#     elif request.node.rep_setup.passed:
    out = request.node
    if request.node.testsfailed != 0:
        tests_list = request.node.items
        for test in tests_list:
            if test.rep_call.failed:
                print("\n executing test failed", test.rep_call.nodeid)

@pytest.fixture(scope="function")
def something(request):
    print "In function"
    yield
    # request.node is an "item" because we use the default
    # "function" scope
#     if request.node.rep_setup.failed:
#         print("setting up a test failed!", request.node.nodeid)
#     elif request.node.rep_setup.passed:
    if request.node.rep_call.failed:
        print("executing test failed", request.node.nodeid)