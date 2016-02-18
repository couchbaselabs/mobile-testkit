import sys
import subprocess
from optparse import OptionParser

# jython imports
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice

def launch_lite_serv(port):

    print('Installing LiteServ on port %d ...' % (port))

    device = MonkeyRunner.waitForConnection()

    success = device.installPackage('/Users/sethrosetter/Code/couchbase-lite-android-liteserv/couchbase-lite-android-liteserv/build/outputs/apk/couchbase-lite-android-liteserv-debug.apk')
    if success:
        print('LiteServ install successful!')
    else:
        print('Could not install LiteServ!')
        sys.exit(1)

    print('Getting Device ip ...')
    result = device.shell('netcfg')
    ip_line = result.split('\n')[0]
    ip = ip_line.split()[2]
    ip = ip.split("/")[0]

    print('Launching LiteServ activity ... ')
    device.shell('am start -a android.intent.action.MAIN -n com.couchbase.liteservandroid/com.couchbase.liteservandroid.MainActivity --ei listen_port %d --es username "" --es password ""' % port)
    print('LiteServ running on %s:%d!' % (ip, port))

    return ip, port

if __name__ == "__main__":

    port = 5984
    args = sys.argv

    if len(args) > 1:
        if args[1].startswith('--port'):
            port_arg = args[1]
            port = int(port_arg.split('=')[1])

    ip, port = launch_lite_serv(port)

