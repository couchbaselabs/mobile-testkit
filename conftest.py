import glob
import sys
import xml
from datetime import datetime, time
from xunit import XUnitTestResult
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
    # file = session.config._htmlfile
    # invoke the file opening in external tool
    # os.system('open ' + "reports/test.xml")




@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    print("reportd data")
    # to remove environment section
    # config._metadata = None
    #
    # if not os.path.exists('reports'):
    #     os.makedirs('reports')
    #
    # config.option.htmlpath = 'reports/' + datetime.now().strftime("%d-%m-%Y %H-%M-%S") + ".html"

def merge_reports(filespath):
    # log.info("Merging of report files from "+str(filespath):
    testsuites = {}
    if not isinstance(filespath, list):
        filespaths = filespath.split(",")
    else:
        filespaths = filespath
    for filepath in filespaths:
        xml_files = glob.glob(filepath)
        if not isinstance(filespath, list) and filespath.find("*"):
            xml_files.sort(key=os.path.getmtime)
        for xml_file in xml_files:
            # log.info("-- " + xml_file + " --")
            doc = xml.dom.minidom.parse(xml_file)
            testsuitelem = doc.getElementsByTagName("testsuite")
            for ts in testsuitelem:
                tsname = ts.getAttribute("name")
                tserros = ts.getAttribute("errors")
                tsfailures = ts.getAttribute("failures")
                tsskips = ts.getAttribute("skips")
                tstime = ts.getAttribute("time")
                tstests = ts.getAttribute("tests")
                issuite_existed = False
                tests = {}
                testsuite = {}
                # fill testsuite details
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
                issuite_existed = False
                testcaseelem = ts.getElementsByTagName("testcase")
                # fill test case details
                for tc in testcaseelem:
                    testcase = {}
                    tcname = tc.getAttribute("name")
                    tctime = tc.getAttribute("time")
                    tcerror = tc.getElementsByTagName("error")

                    tcname_filtered = filter_fields(tcname)

                    testcase['name'] = tcname
                    testcase['time'] = tctime
                    testcase['error'] = ""
                    if tcerror:
                        testcase['error']  = str(tcerror[0].firstChild.nodeValue)

                    tests[tcname_filtered] = testcase
                testsuite['tests'] = tests
                testsuites[tsname] = testsuite

    # log.info("\nNumber of TestSuites="+str(len(testsuites)))
    tsindex = 0
    for tskey in list(testsuites.keys()):
        tsindex = tsindex+1
        # log.info("\nTestSuite#"+str(tsindex)+") "+str(tskey)+", Number of Tests="+str(len(testsuites[tskey]['tests'])))
        pass_count = 0
        fail_count = 0
        tests = testsuites[tskey]['tests']
        xunit = XUnitTestResult()
        for testname in list(tests.keys()):
            testcase = tests[testname]
            tname = testcase['name']
            ttime = testcase['time']
            inttime = float(ttime)
            terrors = testcase['error']
            tparams = ""
            if "," in tname:
                tparams = tname[tname.find(","):]
                tname = tname[:tname.find(",")]

            if terrors:
                failed = True
                fail_count = fail_count + 1
                xunit.add_test(name=tname, status='fail', time=inttime,
                               errorType='membase.error', errorMessage=str(terrors), params=tparams
                               )
            else:
                passed = True
                pass_count = pass_count + 1
                xunit.add_test(name=tname, time=inttime, params=tparams
                    )

        str_time = time.strftime("%y-%b-%d_%H-%M-%S", time.localtime())
        abs_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        root_log_dir = os.path.join(abs_path, "logs{0}testrunner-{1}".format(os.sep, str_time))
        if not os.path.exists(root_log_dir):
            os.makedirs(root_log_dir)
        logs_folder = os.path.join(root_log_dir, "merged_summary")
        try:
            os.mkdir(logs_folder)
        except:
            pass
        output_filepath="{0}{2}mergedreport-{1}".format(logs_folder, str_time, os.sep).strip()

        xunit.write(output_filepath)
        xunit.print_summary()
        # log.info("Summary file is at " + output_filepath+"-"+tsname+".xml")
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
                #log.info("Replacing : with ={}".format(fw))
                line = line + fw.replace(":", "=", 1)
            else:
                line = line + fw
            if fw != testwords[-1]:
                line = line + ","

    return line
