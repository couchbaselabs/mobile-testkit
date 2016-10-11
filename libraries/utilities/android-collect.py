import os.path
import subprocess
import sys
import datetime
from optparse import OptionParser


def validate_args(parser, package_name):
    if package_name is None:
        parser.print_help()
        sys.exit(1)


def get_devices():
    device_ids = []
    device_output = subprocess.check_output(["adb", "devices", "-l"])
    lines = device_output.split('\n')[1:]
    for line in lines[1:]:
        device_id = line.split(' ')[0]
        if len(device_id.strip()) > 0:
            device_ids.append(device_id)
    return device_ids


def create_dump_directory():
    dir_name = "{}-android-dump".format(datetime.datetime.utcnow())
    os.makedirs(dir_name)
    return dir_name


def collect(directory_name, package_name):
    print("Collection starting")

    devices = get_devices()
    for device in devices:
        print("Found device: {}".format(device))

        device_dir = "{}/{}".format(directory_name, device)

        # Create device directory
        os.makedirs(device_dir)

        # Pull adb logs
        logcat_output_file_name = "{}/logcat.txt".format(device_dir)
        logcat_output = subprocess.check_output(["adb", "-s", "{}".format(device), "logcat", "-d", logcat_output_file_name])
        with open(logcat_output_file_name, "w") as f:
            f.write(logcat_output)

        # Kill app to dump threads
        trace_file_name = "{}/traces.txt".format(device_dir)
        subprocess.check_call(["adb", "-s", "{}".format(device), "shell", "am", "force-stop", package_name])

        # Pull trace file
        trace_output = subprocess.check_output(["adb", "-s", "{}".format(device), "shell", "cat /data/anr/traces.txt"])
        with open(trace_file_name, "w") as f:
            f.write(trace_output)


if __name__ == "__main__":

    usage = "usage: android-collect.py -p com.sample.package"

    parser = OptionParser(usage=usage)

    parser.add_option("-p", "--package-name",
                      action="store", type="string", dest="package_name", default=None,
                      help="android package name, ex. com.sample.package")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    validate_args(parser, opts.package_name)

    directory = create_dump_directory()
    collect(directory, opts.package_name)
