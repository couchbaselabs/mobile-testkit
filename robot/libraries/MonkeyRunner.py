import sys
import subprocess

from optparse import OptionParser

# jython imports
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice

def wait_for_emulator(name):
    device = MonkeyRunner.waitForConnection(timeout=120, deviceId=name)
    print("Device running: {}".format(name))
