import sys
import subprocess
import time

from optparse import OptionParser

# jython imports
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice


def reset_and_launch_app(target_device, apk_path, activity, reinstall, is_liteserve):

    print('Waiting for device "%s" ' % target_device)
    device = MonkeyRunner.waitForConnection(timeout=10, deviceId=target_device)

    package_name = activity.split('/')[0]

    if reinstall:
        # Remove + Install the .apk on target
        print ('Removing %s on device "%s"' % (package_name, target_device))
        device.removePackage(package_name)

        print('Installing "%s" on device "%s"' % (apk_path, target_device))
        success = device.installPackage(apk_path)
        if not success:
            print('Failed to install apk. Exiting!')
            sys.exit(1)
    else:
        # Stop app and clear package cache
        print ('Stopping package %s on device "%s"' % (package_name, target_device))
        device.shell("am force-stop %s" % package_name)

        print ('Clearing package cache for %s on device "%s"' % (package_name, target_device))
        device.shell("pm clear %s" % package_name)

    if is_liteserve:
        print('Launching LiteServ: "%s"' % activity)
        device.shell('am start -a android.intent.action.MAIN -n %s --ei listen_port 5984 --es username none --es password none' % activity)
    else:
        print('Launching activity: "%s"' % activity)
        device.startActivity(component=activity)


def parse_args():
    """
    Parse command line args and return a tuple. Monkeyrunner info - https://developer.android.com/studio/test/monkeyrunner/index.html
    """
    parser = OptionParser()
    parser.add_option('', '--target', help="Device name from 'adb devices -l'", dest="target")
    parser.add_option('', '--local-port', help="Local port to forward listener to", type="int", dest="local_port")
    parser.add_option('', '--apk-path', help="Path to apk relative to repo root", dest="apk_path")
    parser.add_option('', '--activity', help="Activity manager activity path", dest="activity")
    parser.add_option('', '--reinstall', help="If set, the apk will be reinstalled", action="store_true", dest="reinstall", default=False)
    (opts, args) = parser.parse_args()
    return parser, opts.target, opts.local_port, opts.apk_path, opts.activity, opts.reinstall


def validate_args(parser, target, local_port, apk_path, package_name, reinstall):
    """
    Make sure all required args are passed, or else print usage
    """
    if target is None:
        parser.print_help()
        exit(-1)

    if apk_path is None:
        parser.print_help()
        exit(-1)
    if package_name is None:
        parser.print_help()
        exit(-1)
    if reinstall is None:
        parser.print_help()
        exit(-1)

    if is_emulator(target):
        if local_port is None:
            parser.print_help()
            exit(-1)


def is_emulator(target):
    return target.startswith("emulator") or target.startswith("192.168")

if __name__ == '__main__':

    parser, target, local_port, apk_path, activity, reinstall = parse_args()
    validate_args(parser, target, local_port, apk_path, activity, reinstall)

    if apk_path.endswith('couchbase-lite-android-liteserv-debug.apk'):
        reset_and_launch_app(target, apk_path, activity, reinstall, True)
    else:
        reset_and_launch_app(target, apk_path, activity, reinstall, False)

    if is_emulator(target):
        # Reset port forwarding
        print('Removing any forwarding rules for local port: %s' % local_port)
        subprocess.call(['adb', '-s', target, 'forward', '--remove', 'tcp:%d' % local_port])

        print('Forwarding %s :5984 to localhost:%s' % (target, local_port))
        subprocess.call(['adb', '-s', target, 'forward', 'tcp:%d' % local_port, 'tcp:5984'])

    time.sleep(20)
