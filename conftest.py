import glob
import sys
import urllib.request
import xml
import xml.dom.minidom
import pytest
import os

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
    file_path = session.config.getoption("--custom-run")
    print(file_path)
    merge_xmls(file_path)
    # os.system('open ' + "results/results.xml")

def pytest_addoption(parser):
    parser.addoption("--custom-run",
                     action="store",
                     help="Sync Gateway mode to run the test in, 'cc' for channel cache or 'di' for distributed index")

@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    print("Starting the tests .....")


def merge_xmls(filepath):
    if filepath.startswith("http://") or filepath.startswith("https://"):
        if filepath.endswith(".xml"):
            url_path = filepath
        else:
            url_path = filepath + "/testReport/api/xml?pretty=true"
        if not os.path.exists('report_logs'):
            os.mkdir('report_logs')
        newfilepath = 'report_logs/' + "_testresult.xml"
        try:
            filedata = urllib.request.urlopen(url_path)
            print(filedata)
            datatowrite = filedata.read()
            file_path = newfilepath
            with open(file_path, 'wb') as f:
                f.write(datatowrite)
        except Exception as ex:
            print("Error:: " + str(ex) + "! Please check if " +
                  url_path + " URL is accessible!!")
            print("Running all the tests instead for now.")
            return None, None

    doc1 = xml.dom.minidom.parse(file_path)
    doc2 = xml.dom.minidom.parse("results/results.xml")
    added_test_count = 0
    testresultelem = doc1.getElementsByTagName("testsuites")
    testresultelem2 = doc2.getElementsByTagName("testsuites")
    testsuitelem = testresultelem[0].getElementsByTagName("testsuite")
    testsuitelem2 = testresultelem2[0].getElementsByTagName("testsuite")
    for ts in testsuitelem:
        testcaseelem = ts.getElementsByTagName("testcase")
        for tc in testcaseelem:
            if not (tc.getElementsByTagName("failure") or tc.getElementsByTagName("error")):
                added_test_count += 1
                doc2.childNodes[0].childNodes[0].appendChild(tc)

    current_test_count = int(testsuitelem2[0].getAttribute("tests")) + added_test_count
    testsuitelem2[0].setAttribute("tests", str(current_test_count))
    print(testsuitelem2[0].toxml())
    doc2.toxml()
    doc2.writexml(open('results/results.xml', 'w'),
               indent="  ",
               addindent="  ",
               newl='\n')
    doc2.unlink()

