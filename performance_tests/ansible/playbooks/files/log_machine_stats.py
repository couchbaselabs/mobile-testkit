#!/usr/bin/python

import time
import datetime
import psutil
import json


def is_running(process_name):
    for p in psutil.process_iter():
        if p.name() == process_name:
            return True
    return False

with open("cpu_stats.json", "w") as f:

    obj = dict()

    # collect cpu stats while sync_gateway process is running
    while is_running("sync_gateway"):

        print("Datetime: {}".format(datetime.datetime.now()))
        print("-------------------------------")
        print("CPU times: {}".format(psutil.cpu_times()))
        print("CPU times (per CPU): {}".format(psutil.cpu_times(percpu=True)))
        print("CPU percent: {}".format(psutil.cpu_percent(interval=1)))
        print("CPU percent (per CPU): {}".format(psutil.cpu_percent(interval=1, percpu=True)))
        print("Virtual memory: {}".format(psutil.virtual_memory()))
        print("Swap memory: {}".format(psutil.swap_memory()))

        current_datetime = "{}".format(datetime.datetime.now())
        obj[current_datetime] = dict()
        obj[current_datetime]["cpu_times"] = psutil.cpu_times()
        obj[current_datetime]["cpu_times_per_cpu"] = psutil.cpu_times(percpu=True)
        obj[current_datetime]["cpu_percent"] = psutil.cpu_percent(interval=1)
        obj[current_datetime]["cpu_percent_per_cpu"] = psutil.cpu_percent(interval=1, percpu=True)
        obj[current_datetime]["virtual_memory"] = psutil.virtual_memory()._asdict()
        obj[current_datetime]["swap_memory"] = psutil.swap_memory()._asdict()

        # Wait 10 seconds
        time.sleep(10)

    # Write stats human readible
    f.write(json.dumps(obj, indent=4))

