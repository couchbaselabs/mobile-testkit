#!/usr/bin/python

# Collect profile data as PDFs and create a .tar.gz file

import os
import shutil
import sys
import psutil
import time
import argparse

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


def collect_profiles(results_directory, sg_binary_path, profile_types, format_types):

    # make sure raw profile gz files end up in results dir
    os.environ["PPROF_TMPDIR"] = results_directory

    for profile_type in profile_types:
        for format_type in format_types:
            print("Collecting {0} profile in format {1}".format(profile_type, format_type))
            out_filename = "{0}.{1}".format(profile_type, format_type)
            dest_path = os.path.join(results_directory, out_filename)
            cmd = "go tool pprof -{0} {1} {2}/{3} > {4}".format(
                format_type,
                sg_binary_path,
                sg_pprof_url,
                profile_type,
                dest_path
            )
            print(cmd)
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


def collect_profile_loop(final_results_directory, profile_types, format_types, delay_secs):

    os.makedirs("/tmp/sync_gateway_profile/")

    while is_running("sync_gateway") or is_running("sg_accel"):

        print("Collecting ...")

        # this is the temp dir where collected files will be stored. will be deleted at end.

        results_directory = "/tmp/sync_gateway_profile_temp"
        if os.path.exists(results_directory):
            print("Deleting temp directory")
            shutil.rmtree(results_directory)
        os.makedirs(results_directory)

        collect_profiles(
            results_directory,
            sg_binary_path,
            profile_types,
            format_types,
        )

        compress_and_copy(results_directory, final_results_directory)

        # delete the tmp dir since we're done with it
        shutil.rmtree(results_directory)

        # package the all of the profile results
        run_command("tar cvfz {0}.tar.gz {1}".format(final_results_directory, final_results_directory))

        print("Waiting {} before collecting next profile".format(delay_secs))

        time.sleep(delay_secs)


    shutil.rmtree(final_results_directory)


if __name__ == "__main__":

    main_final_results_directory = "/tmp/sync_gateway_profile"

    if os.path.exists(main_final_results_directory):
        print("Deleting existing directory")
        shutil.rmtree(main_final_results_directory)

    if os.path.exists("{0}.tar.gz".format(main_final_results_directory)):
        print("Removing existing results")
        os.remove("{0}.tar.gz".format(main_final_results_directory))

    parser = argparse.ArgumentParser()
    parser.add_argument("--sg-binary", help="Path to Sync Gateway binary", required=True)
    parser.add_argument("--format-type-pdf", help="Collect pdf format", action='store_true', default=False)
    parser.add_argument("--format-type-text", help="Collect text format", action='store_true', default=False)
    parser.add_argument("--profile-type-cpu", help="Collect cpu profile", action='store_true', default=False)
    parser.add_argument("--profile-type-heap", help="Collect heap profile", action='store_true', default=False)
    parser.add_argument("--profile-type-goroutine", help="Collect goroutine profile", action='store_true', default=False)
    parser.add_argument("--delay-secs", help="How long to delay in between collections in seconds", default=(9*60))  # mins

    args = parser.parse_args()

    sg_binary_path = args.sg_binary

    format_types = []
    profile_types = []

    if args.format_type_pdf:
        format_types.append("pdf")
    if args.format_type_text:
        format_types.append("text")

    if len(format_types) == 0:
        raise Exception("You must select at least one format type")

    if args.profile_type_cpu:
        profile_types.append("profile")
    if args.profile_type_heap:
        profile_types.append("heap")
    if args.profile_type_goroutine:
        profile_types.append("goroutine")

    if len(profile_types) == 0:
        raise Exception("You must select at least one profile type")

    collect_profile_loop(
        main_final_results_directory,
        profile_types,
        format_types,
        int(args.delay_secs),
    )
