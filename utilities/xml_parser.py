import glob
import xml.dom.minidom
from optparse import OptionParser
import urllib.request
import urllib
import sys
import os
import uuid


def parse_junit_result_xml(filepath=""):
    if filepath.startswith("http://") or filepath.startswith("https://"):
        return parse_testreport_result_xml(filepath)
    if filepath == "":
        filepath = "logs/**/*.xml"
    print("Loading result data from " + filepath)
    xml_files = glob.glob(filepath)
    passed_tests = []
    failed_tests = []
    for xml_file in xml_files:
        print("-- " + xml_file + " --")
        doc = xml.dom.minidom.parse(xml_file)
        testsuitelem = doc.getElementsByTagName("testsuite")
        for ts in testsuitelem:
            testcaseelem = ts.getElementsByTagName("testcase")
            failed = False
            for tc in testcaseelem:
                tcname = tc.getAttribute("name")
                tcerror = tc.getElementsByTagName("error")
                for tce in tcerror:
                    failed_tests.append(tcname)
                    failed = True
                if not failed:
                    passed_tests.append(tcname)

    if failed_tests:
        failed_tests = transform_and_write_to_file(failed_tests, "failed_tests.conf")
        print(" or ".join(failed_tests))

    if passed_tests:
        passed_tests = transform_and_write_to_file(passed_tests, "passed_tests.conf")


def parse_testreport_result_xml(filepath=""):
    if filepath.startswith("http://") or filepath.startswith("https://"):
        if filepath.endswith(".xml"):
            url_path = filepath
        else:
            url_path = filepath + "/testReport/api/xml?pretty=true"
        jobnamebuild = filepath.split('/')
        if not os.path.exists('logs'):
            os.mkdir('logs')
        newfilepath = 'logs' + ''.join(os.sep) + '_'.join(jobnamebuild[-3:]) + "_testresult.xml"
        # print("Downloading " + url_path + " to " + newfilepath)
        try:
            filedata = urllib.request.urlopen(url_path)
            datatowrite = filedata.read()
            filepath = newfilepath
            with open(filepath, 'wb') as f:
                f.write(datatowrite)
        except Exception as ex:
            print("Error:: " + str(ex) + "! Please check if " +
                  url_path + " URL is accessible!!")
            print("Running all the tests instead for now.")
            return None, None
    if filepath == "":
        filepath = "logs/**/*.xml"
    xml_files = glob.glob(filepath)
    passed_tests = []
    failed_tests = []
    for xml_file in xml_files:
        doc = xml.dom.minidom.parse(xml_file)
        testresultelem = doc.getElementsByTagName("testsuites")
        testsuitelem = testresultelem[0].getElementsByTagName("testsuite")
        for ts in testsuitelem:
            testcaseelem = ts.getElementsByTagName("testcase")
            for tc in testcaseelem:
                tcname = tc.getAttribute("name")
                if tc.getElementsByTagName("failure") or tc.getElementsByTagName("error"):
                    failed_tests.append(tcname)
                else:
                    passed_tests.append(tcname)

    if failed_tests:
        failed_tests = transform_and_write_to_file(failed_tests, "failed_tests.conf")

    if passed_tests:
        passed_tests = transform_and_write_to_file(passed_tests, "passed_tests.conf")
    print(" or ".join(failed_tests))
    p_file = open("test_passed", "w+")
    p_file.write(" or ".join(passed_tests))
    f_file = open("test_failures", "w+")
    f_file.write(" or ".join(failed_tests))
    return passed_tests, failed_tests


def getNodeText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


def check_if_exists(test_list, test_line):
    new_test_line = ''.join(sorted(test_line))
    for t in test_list:
        t1 = ''.join(sorted(t))
        if t1 == new_test_line:
            return True, t
    return False, ""


def transform_and_write_to_file(tests_list, filename):
    new_test_list = []
    for test in tests_list:
        line = filter_fields(test)
        line = line.rstrip(",")
        isexisted, _ = check_if_exists(new_test_list, line)
        if not isexisted:
            new_test_list.append(line)

    file = open(filename, "w+")
    for line in new_test_list:
        file.writelines((line) + "\n")
    file.close()
    return new_test_list


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
            if "\":" not in fw or "query:" in fw:
                # log.info("Replacing : with ={}".format(fw))
                line = line + fw.replace(":", "=", 1)
            else:
                line = line + fw
            if fw != testwords[-1]:
                line = line + ","

    return line


def custom_rerun_xml_merge(filepath, type):
    if filepath.startswith("http://") or filepath.startswith("https://"):
        if filepath.endswith(".xml"):
            url_path = filepath
        else:
            url_path = filepath + "/testReport/api/xml?pretty=true"
        if not os.path.exists('results'):
            os.mkdir('results')
        newfilepath = 'results/' + "_testresult.xml"
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
    else:
        file_path = filepath

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
            if type == "fail":
                if not (tc.getElementsByTagName("failure") or tc.getElementsByTagName("error")):
                    added_test_count += 1
                    doc2.childNodes[0].childNodes[0].appendChild(tc)
            if type == "pass":
                if tc.getElementsByTagName("failure") or tc.getElementsByTagName("error"):
                    added_test_count += 1
                    doc2.childNodes[0].childNodes[0].appendChild(tc)

    current_test_count = int(testsuitelem2[0].getAttribute("tests")) + added_test_count
    testsuitelem2[0].setAttribute("tests", str(current_test_count))
    # print(testsuitelem2[0].toxml())
    doc2.toxml()
    doc2.writexml(open('results/results.xml', 'w'),
                  indent="  ",
                  addindent="  ",
                  newl='\n')
    doc2.unlink()


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
        if not os.path.exists('results'):
            os.mkdir('results')
        newfilepath = 'results/' + str(uuid.uuid4()) + "_testresult.xml"
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
    xml_files = glob.glob("results/*.xml")
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
    output_filepath = 'results/new_results.xml'
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
        tclass = testcase['classname']
        ttime = testcase['time']
        inttime = float(ttime)
        terrors = testcase['error']
        tfailure = testcase['failure']
        tfailure_message = testcase['failure-message']
        terror_message = testcase['error-message']
        file = testcase['file']
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

    xml_testsuites.appendChild(xml_testsuite)
    doc.appendChild(xml_testsuites)
    f = open(output_filepath, "w+")
    f.write(doc.toprettyxml())
    f.close()
    print("Summary file is at " + output_filepath)
    return testsuites


def compare_with_sort(dict, key):
    for k in list(dict.keys()):
        if "".join(sorted(k)) == "".join(sorted(key)):
            return True
    return False


if __name__ == "__main__":
    usage = """usage: xml_parser.py
       usage: python mobile_server_pool.py
       --file=xml-file path
       """
    parser = OptionParser(usage=usage)

    parser.add_option("--xml-file",
                      action="store", dest="xml_file",
                      default="http://uberjenkins.sc.couchbase.com:8080/job/cen7-sync-gateway-functional-tests-sgreplicate2/lastCompletedBuild/artifact/results/results.xml",
                      help="File-path")
    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)
    if opts.xml_file:
        parse_junit_result_xml(opts.xml_file)
    else:
        raise Exception("Use either one the flag from --xml-file")
