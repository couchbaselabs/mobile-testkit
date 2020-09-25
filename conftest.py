import time

import urllib.request
import xml
import xml.dom.minidom
import pytest
import os
import uuid
import glob
from xunit import XUnitTestResult


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
    if session.config.getoption("--custom-run"):
        file_path = session.config.getoption("--custom-run")
        merge_xmls(file_path)


def pytest_addoption(parser):
    parser.addoption("--custom-run",
                     action="store",
                     help="xml file to be merged")

    parser.addoption("--merge", action="store",
                     help="Merge the report files path pattern, like logs/**/.xml. e.g.  -m '["
                          "logs/**/*.xml]'",
                     default="")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    print("Starting the tests .....")


def merge_reports(filespath):
    print("Merging of report files from " + str(filespath))
    testsuites = {}
    tests = {}
    testsuite = {}
    filepaths = filespath.split(",")
    for filepath in filepaths:
        if filepath.startswith("http://") or filepath.startswith("https://"):
            if filepath.endswith(".xml"):
                url_path = filepath
            else:
                url_path = filepath + "/testReport/api/xml?pretty=true"
        if not os.path.exists('report_logs'):
            os.mkdir('report_logs')
        newfilepath = 'report_logs/' + str(uuid.uuid4()) + "_testresult.xml"
        try:
            print(url_path)
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
    xml_files = glob.glob("report_logs/*.xml")
    errors = 0
    failures = 0
    for xml_file in xml_files:
        print("-- " + xml_file + " --")
        doc = xml.dom.minidom.parse(xml_file)
        suites = doc.getElementsByTagName("testsuites")
        testsuitelem = suites[0].getElementsByTagName("testsuite")
        for ts in testsuitelem:
            tsname = ts.getAttribute("name")
            tserros = ts.getAttribute("errors")
            tsfailures = ts.getAttribute("failures")
            tsskips = ts.getAttribute("skips")
            tstime = ts.getAttribute("time")
            tstests = ts.getAttribute("tests")


            # # fill testsuite details
            if tsname in list(testsuites.keys()):
                testsuite = testsuites[tsname]
                tests = testsuite['tests']
            else:
                testsuite['name'] = tsname
            testsuite['errors'] = tserros
            testsuite['failures'] = tsfailures
            testsuite['skips'] = tsskips
            testsuite['time'] = tstime
            testsuite['testcount'] = tstests
            testcaseelem = ts.getElementsByTagName("testcase")
            # fill test case details
            for tc in testcaseelem:
                testcase = {}
                tcname = tc.getAttribute("name")
                tcclass = tc.getAttribute("classname")
                tctime = tc.getAttribute("time")
                tcfile = tc.getAttribute("file")
                tcerror = tc.getElementsByTagName("error")
                tcfailure = tc.getElementsByTagName("failure")
                tcname_filtered = filter_fields(tcname)
                if compare_with_sort(tests, tcname_filtered):
                    testcase = tests[tcname_filtered]
                    testcase['name'] = tcname
                else:
                    testcase['name'] = tcname
                testcase['time'] = tctime
                testcase['error'] = ""
                testcase['failure-message'] = ""
                testcase['error-message'] = ""
                testcase['failure'] = ""
                testcase['classname'] = tcclass
                testcase['file'] = tcfile
                if tcerror:
                    errors += 1
                    testcase['error'] = str(tcerror[0].firstChild.nodeValue)
                    testcase['error-message'] = tcerror[0].getAttribute("message")
                if tcfailure:
                    failures += 1
                    testcase['failure'] = str(tcfailure[0].firstChild.nodeValue)
                    testcase['failure-message'] = tcfailure[0].getAttribute("message")
                if tcname_filtered in list(tests.keys()):
                    if not testcase['failure']:
                        failures -= 1
                        del tests[tcname_filtered]
                        tests[tcname_filtered] = testcase
                    if not testcase['error']:
                        errors -= 1
                        del tests[tcname_filtered]
                        tests[tcname_filtered] = testcase
                else:
                    tests[tcname_filtered] = testcase
    # print(list(tests.keys()))
    testsuite['tests'] = tests
    output_filepath = 'report_logs/report.xml'
    f = open(output_filepath, "w+")
    f.close()
    doc = xml.dom.minidom.Document()
    xml_testsuites = doc.createElement('testsuites')
    xml_testsuite = doc.createElement('testsuite')

    # <testsuite name="nosetests" tests="1" errors="1" failures="0" skip="0">
    xml_testsuite.setAttribute('errors', str(errors))
    xml_testsuite.setAttribute('failures', str(failures))
    xml_testsuite.setAttribute('skips', str(testsuite["skips"]))
    xml_testsuite.setAttribute('tests', str(len(tests.keys())))
    xml_testsuite.setAttribute('time', str(testsuite["time"]))
    xml_testsuite.setAttribute('name', "pytest")
    xml_testsuites.appendChild(xml_testsuite)
    for testname in tests.keys():
        testcase = tests[testname]
        tname = testcase['name']
        tclass= testcase['classname']
        ttime = testcase['time']
        inttime = float(ttime)
        terrors = testcase['error']
        tfailure = testcase['failure']
        tfailure_message = testcase['failure-message']
        terror_message = testcase['error-message']
        file = testcase['file']
        tparams = ""
        testcase = doc.createElement('testcase')
        testcase.setAttribute('name', tname)
        testcase.setAttribute('classname', tclass)
        testcase.setAttribute('file', str(file))
        testcase.setAttribute('time', str(inttime))
        if tfailure:
            failure = doc.createElement('failure')
            failure.setAttribute('message', tfailure_message)
            txt = doc.createTextNode(tfailure)
            failure.appendChild(txt)
            testcase.appendChild(failure)
        if terrors:
            error = doc.createElement('error')
            error.setAttribute('message', terror_message)
            txt = doc.createTextNode(terrors)
            error.appendChild(txt)
            testcase.appendChild(error)
        xml_testsuite.appendChild(testcase)


            # xunit.print_summary()
    xml_testsuites.appendChild(xml_testsuite)
    doc.appendChild(xml_testsuites)
    f = open(output_filepath, "w+")
    f.write(doc.toprettyxml())
    f.close()
    print("Summary file is at " + output_filepath)
    return testsuites


def filter_fields(testname):
    testwords = testname.split(",")
    line = ""
    for fw in testwords:
        if not fw.startswith("logs_folder") and not fw.startswith("conf_file") \
                and not fw.startswith("cluster_name:") \
                and not fw.startswith("ini:") \
                and not fw.startswith("case_number:") \
                and not fw.startswith("num_nodes:") \
                and not fw.startswith("spec:"):
            if not "\":" in fw or "query:" in fw:
                # log.info("Replacing : with ={}".format(fw))
                line = line + fw.replace(":", "=", 1)
            else:
                line = line + fw
            if fw != testwords[-1]:
                line = line + ","
    return line


def compare_with_sort(dict, key):
    for k in list(dict.keys()):
        if "".join(sorted(k)) == "".join(sorted(key)):
            return True
    return False


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
