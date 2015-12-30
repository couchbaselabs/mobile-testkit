import json
import datetime
import os
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

matplotlib.rcParams.update({'font.size': 8})

def keys_present(keys, dictionary):
    for key in keys:
        if key not in dictionary:
            # only plot timestamps with all info
            return False
    return True


def plot_expvars(figure, json_file_name):

    obj = dict()
    with open(json_file_name, "r") as f:
        obj = json.loads(f.read())

    datetimes = []
    p95 = []
    p99 = []
    docs_pushed = []
    docs_pulled = []

    for entry in obj.keys():
        print(entry)
        print(obj[entry])

        # only plot entry with all vars wer are looking for
        if keys_present(["p95", "p99", "total_doc_pushed", "total_doc_pulled"], obj[entry]):
            datetimes.append(datetime.datetime.strptime(entry, "%Y-%m-%d %H:%M:%S.%f"))
            p95.append(obj[entry]["p95"])
            p99.append(obj[entry]["p99"])
            docs_pushed.append(obj[entry]["total_doc_pushed"])
            docs_pulled.append(obj[entry]["total_doc_pulled"])


    # Plot p95 / p99
    ax1 = figure.add_subplot(211)
    ax1.set_title(" p95 (blue) / p99 ns (g)")
    ax1.plot(datetimes, p95, "bs", datetimes, p99, "g^")
    for i, j in zip(datetimes, p95):
        ax1.annotate(str(j), xy=(i, j))

    # Plot docs pushed / docs pulled
    ax2 = figure.add_subplot(212)
    ax2.set_title("docs pushed (red) / docs pulled (yellow)")
    ax2.plot(datetimes, docs_pushed, "rs", datetimes, docs_pulled, "y^")

    figure.autofmt_xdate()


def plot_machine_stats(figure, folder_path):

    folders = [x[0] for x in os.walk(folder_path)]

    machine_stats = dict()
    # entry at one is the first subdirect
    for subfolder in folders[1:]:

        # Get name of sg
        path_components = os.path.split(subfolder)
        name = path_components[len(path_components) - 1]

        # Get CPU stats dict for sg
        with open("{}/cpu_stats.json".format(subfolder), "r") as f:
            obj = json.loads(f.read())
            machine_stats[name] = obj

    ax3 = figure.add_subplot(111)
    ax3.set_title("CPU percent")

    count = 0
    for machine in machine_stats:
        entity = machine_stats[machine]

        entity_timestamps = [datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f") for timestamp in entity.keys()]
        cpu_percents = [entity[timestamp]["cpu_percent"] for timestamp in entity.keys()]

        # Hack to show differenct machines in different color
        if machine == "sg1":
            color = "r"
        elif machine == "sg2":
            color = "g"
        elif machine == "sg3":
            color = "b"
        else:
            color = "y"

        ax3.plot(entity_timestamps, cpu_percents, "{}o".format(color))
        count += 1

    figure.autofmt_xdate()


fig1 = plt.figure()
fig1.text(0.5, 0.04, 'Gateload Expvars', ha='center', va='center')

# Generate plot of gateload expvars
plot_expvars(fig1, "performance_results/Test6/2015-12-29-17-16-30-expvars.json")

plt.savefig("expvars.png", dpi=300)

fig2 = plt.figure()
fig2.text(0.5, 0.04, 'sync_gateway CPU', ha='center', va='center')

# Generate plot of machine stats
plot_machine_stats(fig2, "performance_results/Test6/2015-12-29-17-18-22-machine-stats/")

# Save png
plt.savefig("sync_gateway.png", dpi=300)