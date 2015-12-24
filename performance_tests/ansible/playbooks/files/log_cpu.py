import time
import datetime
import psutil


def is_running(process_name):
    for p in psutil.process_iter():
        if p.name() == process_name:
            return True
    return False

with open("cpu_stats", "w") as f:

    # collect cpu stats while gateload process is running
    while is_running("gateload"):

        f.write(datetime.datetime.now())
        print(psutil.cpu_percent())

