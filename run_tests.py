import sys
import pytest
import os

import shutil

from optparse import OptionParser

if __name__ == "__main__":
    usage = """
    usage: python run_tests.py
    usage: python run_tests.py -t test_samplefile
    usage: python run_tests.py -t test_samplefile.py::test_test1
    usage: python run_tests.py -m sanity
    """

    parser = OptionParser(usage=usage)

    parser.add_option("-t", "",
                      action="store",
                      type="string",
                      dest="test",
                      default=None,
                      help="test or fixture to run")

    parser.add_option("-m", "",
                      action="store",
                      type="string",
                      dest="mark",
                      default=None,
                      help="pytest mark to target")

    parser.add_option("-r", "",
                      action="store",
                      type="int",
                      dest="repeat",
                      default=1,
                      help="repeat number of times (only works with -t)")

    (opts, args) = parser.parse_args(sys.argv[1:])

    # Delete sg logs in /tmp
    filelist = [f for f in os.listdir("/tmp") if f.endswith(".zip") or f.endswith("sglogs")]
    for f in filelist:
        if os.path.isfile("/tmp/" + f):
            os.remove("/tmp/" + f)
        else:
            shutil.rmtree("/tmp/" + f)

    if opts.test:
        count = 0
        while count < opts.repeat:
            status = pytest.main("--capture=no --junit-xml=results.xml {}".format(opts.test))
            if status != 0:
                break
            count += 1

    elif opts.mark:
        pytest.main("--capture=no --junit-xml=results.xml -m {}".format(opts.mark))
    else:
        pytest.main("--capture=no --junit-xml=results.xml")
