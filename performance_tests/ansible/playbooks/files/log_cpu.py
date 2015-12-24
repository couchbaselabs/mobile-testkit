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

        print("Datetime: {}".format(datetime.datetime.now()))
        print("-------------------------------")
        print("CPU times: {}".format(psutil.cpu_times()))
        print("CPU times (per CPU): {}".format(psutil.cpu_times(percpu=True)))
        print("CPU percent: {}".format(psutil.cpu_percent(interval=1)))
        print("CPU percent (per CPU): {}".format(psutil.cpu_percent(interval=1, percpu=True)))

        f.write("Datetime: {}\n".format(datetime.datetime.now()))
        f.write("-------------------------------\n")
        f.write("CPU times: {}\n".format(psutil.cpu_times()))
        f.write("CPU times (per CPU): {}\n".format(psutil.cpu_times(percpu=True)))
        f.write("CPU percent: {}\n".format(psutil.cpu_percent(interval=1)))
        f.write("CPU percent (per CPU): {}\n".format(psutil.cpu_percent(interval=1, percpu=True)))

        f.write("\n\n")
        # Wait a minute
        time.sleep(1)

