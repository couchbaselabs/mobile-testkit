import xml
from datetime import datetime, time

import glob
import xml.dom.minidom
from optparse import OptionParser
import urllib.request
import os
import urllib
import sys
from xml.etree import ElementTree, ElementInclude

def merge_xmls(file_paths):
    file_paths = file_paths.split(',')
    doc1 = xml.dom.minidom.parse("/Users/manasaghanta/Documents/mobile-test/DailyCode-changes/mobile-testkit/xml2.xml")
    doc2 = xml.dom.minidom.parse("/Users/manasaghanta/Documents/mobile-test/DailyCode-changes/mobile-testkit/xm1.xml")
    added_test_count = 0
    testresultelem = doc1.getElementsByTagName("testsuites")
    testresultelem2 = doc2.getElementsByTagName("testsuites")
    testsuitelem = testresultelem[0].getElementsByTagName("testsuite")
    testsuitelem2 = testresultelem2[0].getElementsByTagName("testsuite")
    for ts in testsuitelem:
        testcaseelem = ts.getElementsByTagName("testcase")
        for tc in testcaseelem:
            if not tc.getElementsByTagName("failure") or tc.getElementsByTagName("error"):
                added_test_count += 1
                doc2.childNodes[0].childNodes[0].appendChild(tc)

    current_test_count = int(testsuitelem2[0].getAttribute("tests")) + added_test_count
    testsuitelem2[0].setAttribute("tests", str(current_test_count))
    doc2.toxml()
    doc2.writexml(open('results/results.xml', 'w'),
               indent="  ",
               addindent="  ",
               newl='\n')
    doc2.unlink()

if __name__ == "__main__":
    usage = """usage: xml_parser.py
       usage: python mobile_server_pool.py
       --file=xml-file path
       """
    parser = OptionParser(usage=usage)

    parser.add_option("--xml-file",
                      action="store", dest="xml_files",
                      default="http://uberjenkins.sc.couchbase.com:8080/job/cen7-sync-gateway-functional-tests-sgreplicate2/lastCompletedBuild/artifact/results/results.xml",
                      help="File-path")
    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)
    if opts.xml_files:
        merge_xmls(opts.xml_files)
    else:
        raise Exception("Use either one the flag from --xml-file")
