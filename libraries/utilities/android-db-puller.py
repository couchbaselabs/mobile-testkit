import subprocess
import sys
from optparse import OptionParser


def validate_args(parser, package_name, target):
    if package_name is None:
        parser.print_help()
        sys.exit(1)

    if target is None:
        parser.print_help()
        sys.exit(1)


def collect(package_name, target_name):
    # Create backup
    # adb -s <device-name> backup -f ~/backup.ab com.sample.package
    adb_output = subprocess.check_output(["adb", "-s", target_name, "backup", "backup.ab", package_name])
    print(adb_output)

    # Extract backup TODO
    # dd if=data.ab bs=1 skip=24 | python -c "import zlib,sys;sys.stdout.write(zlib.decompress(sys.stdin.read()))" | tar -xvf -

if __name__ == "__main__":

    usage = """usage: collect.py
    -p com.test.sample
    -t 01234565789101112
    """

    parser = OptionParser(usage=usage)

    parser.add_option("-p", "--package-name",
                      action="store", type="string", dest="package_name", default=None,
                      help="android package name, ex. com.sample.package")

    parser.add_option("-t", "--target",
                      action="store", type="string", dest="target", default=None,
                      help="device id to collect from 01234565789101112")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    validate_args(parser, opts.package_name, opts.target)
    collect(opts.package_name, opts.target)
