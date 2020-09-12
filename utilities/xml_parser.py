import logging

import signal
import shutil
import glob
import xml.dom.minidom
from optparse import OptionParser
import urllib.request
from http.client import BadStatusLine
import os
import urllib
import sys


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
            tsname = ts.getAttribute("name")
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
                    failed = True
                    failed_tests.append(tcname.split('[')[0])
                else:
                    failed = False
                    passed_tests.append(tcname)

    if failed_tests:
        failed_tests = transform_and_write_to_file(failed_tests, "failed_tests.conf")

    if passed_tests:
        passed_tests = transform_and_write_to_file(passed_tests, "passed_tests.conf")
    print(" or ".join(failed_tests))
    f_file = open("test_failures", "w+")
    f_file.write(" or ".join(failed_tests))
    p_file = open("test_passed", "w+")
    p_file.write(" or ".join(passed_tests))
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
            if not "\":" in fw or "query:" in fw:
                # log.info("Replacing : with ={}".format(fw))
                line = line + fw.replace(":", "=", 1)
            else:
                line = line + fw
            if fw != testwords[-1]:
                line = line + ","

    return line


if __name__ == "__main__":
    usage = """usage: xml_parser.py
       usage: python mobile_server_pool.py
       --file=xml-file path
       """
    parser = OptionParser(usage=usage)

    parser.add_option("--xml-file",
                      action="store", dest="xml_file", default="http://uberjenkins.sc.couchbase.com:8080/job/cen7-sync-gateway-functional-tests-sgreplicate2/lastCompletedBuild/artifact/results/results.xml",
                      help="File-path")
    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)
    if opts.xml_file:
        parse_junit_result_xml(opts.xml_file)
    else:
        raise Exception("Use either one the flag from --xml-file")
