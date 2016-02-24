#!/usr/bin/python

## Collect profile data as PDFs and create a .tar.gz file

import os
import shutil
import sys
import tempfile
import psutil
import time


profile_types = [
    "profile",
    "heap",
    "goroutine",
]

format_types = [
    "pdf",
    "text",
]

sg_pprof_url = "http://localhost:4985/_debug/pprof"


def is_running(process_name):
    for p in psutil.process_iter():
        if p.name() == process_name:
            return True
    return False


def run_command(command):
    return_val = os.system(command)
    if return_val != 0:
        raise Exception("{0} failed".format(command))


def collect_profiles(results_directory, sg_binary_path):

    # make sure raw profile gz files end up in results dir
    os.environ["PPROF_TMPDIR"] = results_directory

    for profile_type in profile_types:
        for format_type in format_types:
            print "Collecting {0} profile in format {1}".format(profile_type, format_type)
            out_filename = "{0}.{1}".format(profile_type, format_type)
            dest_path = os.path.join(results_directory, out_filename)
            cmd = "go tool pprof -{0} {1} {2}/{3} > {4}".format(
                format_type,
                sg_binary_path,
                sg_pprof_url,
                profile_type,
                dest_path
            )
            print cmd
            run_command(cmd)


def compress_and_copy(results_directory, final_results_directory):

    date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
    filename = "{}_profile_data.tar.gz".format(date_time)

    # Navigate to profile data, compress the results, return to cwd
    cwd = os.getcwd()
    os.chdir(results_directory)
    run_command("tar cvfz {0} *".format(filename))
    os.chdir(cwd)

    # Copy compressed results to final directory
    shutil.copy("{0}/{1}".format(results_directory, filename), final_results_directory)


if __name__ == "__main__":

    # get commit from command line args and validate
    if len(sys.argv) <= 1:
        raise Exception("Usage: {0} <path-sync-gw-binary>".format(sys.argv[0]))

    sg_binary_path = sys.argv[1]

    final_results_directory = "/tmp/sync_gateway_profile"

    if os.path.exists(final_results_directory):
        print("Deleting existing directory")
        shutil.rmtree(final_results_directory)

    if os.path.exists("{0}.tar.gz".format(final_results_directory)):
        print("Removing existing results")
        os.remove("{0}.tar.gz".format(final_results_directory))

    os.makedirs("/tmp/sync_gateway_profile/")

    minutes_elapsed = 0
    while is_running("sync_gateway") or is_running("sg_accel"):

        print("Polling ...")

        # only cature profile every ~9 mins
        if minutes_elapsed % 9 == 0:

            print("Collecting ...")

            # this is the temp dir where collected files will be stored. will be deleted at end.

            results_directory = "/tmp/sync_gateway_profile_temp"
            os.makedirs(results_directory)

            collect_profiles(results_directory, sg_binary_path)

            compress_and_copy(results_directory, final_results_directory)

            # delete the tmp dir since we're done with it
            shutil.rmtree(results_directory)

            # takes 1 min for collection
            minutes_elapsed += 1
            continue

        # wait five minutes
        time.sleep(60)
        minutes_elapsed += 1

    # package the all of the profile results
    run_command("tar cvfz {0}.tar.gz {1}".format(final_results_directory, final_results_directory))

    shutil.rmtree(final_results_directory)
