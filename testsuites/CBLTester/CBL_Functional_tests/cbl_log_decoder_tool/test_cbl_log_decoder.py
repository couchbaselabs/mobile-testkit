import pytest
import os
import requests
import shutil

from zipfile import ZipFile
from keywords.constants import BINARY_DIR
from keywords.constants import RELEASED_BUILDS
from keywords.constants import LATEST_BUILDS
from CBLClient.FileLogging import FileLogging
from keywords.utils import log_info
from libraries.provision.ansible_runner import AnsibleRunner


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.database
def test_cbl_decoder_with_existing_logs(params_from_base_test_setup):
    """
    @summary:
    1.Get the cbl log decoder tool based on the build number provided
    2.Decode all binary logs of each release version and verify logs got decoded
    """
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cbl_log_decoder_platform = params_from_base_test_setup["cbl_log_decoder_platform"]
    cbl_log_decoder_build = params_from_base_test_setup["cbl_log_decoder_build"]

    log_dir = "resources/data/cbl_logs"
    cbl_platforms = ["iOS", "xamarin-android", "Net-core", "uwp", "xamarin-ios", "Android"]
    versions = ["2.5.0"]

    for platform in cbl_platforms:
        for version in versions:
            cbl_log_dir = "{}/{}/{}".format(log_dir, version, platform)
            cbl_logs = os.listdir(cbl_log_dir)
            extracted_cbllog_directory_name = download_cbl_log(cbl_log_decoder_platform, liteserv_version, cbl_log_decoder_build)
            for log in cbl_logs:
                file = "{}/{}".format(cbl_log_dir, log)
                assert is_binary(file), "{} file is not binary ".format(file)
                decode_logs(extracted_cbllog_directory_name, file)


@pytest.mark.listener
@pytest.mark.database
def test_cbl_decoder_with_current_logs(params_from_base_test_setup):
    """
    @summary:
    1.Get the cbl log decoder tool based on the build number provided
    2.Run some basic flow on cbl like create bulk docs
    3. Pull logs from cbl client to local machine to /tmp/test directory
    4. Verify logs are binary
    5. Use the decoder tool and decode the logs and verify logs are not binary after decoding
    """
    base_url = params_from_base_test_setup["base_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    cbl_log_decoder_platform = params_from_base_test_setup["cbl_log_decoder_platform"]
    cbl_log_decoder_build = params_from_base_test_setup["cbl_log_decoder_build"]
    log_file = params_from_base_test_setup["test_db_log_file"]
    device_enabled = params_from_base_test_setup["device_enabled"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    log_obj = FileLogging(base_url)
    num_of_docs = 10
    channels_sg = ["ABC"]
    log_level = "verbose"
    plain_text = False
    if liteserv_platform == "net-msft" or liteserv_platform == "net-uwp":
        cbl_log_dir = log_file
    else:
        cbl_log_dir = "/tmp/test"
    # Clean up test directory to remove stale logs
    if os.path.exists(cbl_log_dir):
        shutil.rmtree(cbl_log_dir)
    if liteserv_platform == "android" or liteserv_platform == "xamarin-android":
        if device_enabled:
            command = "adb -d shell mkdir /tmp/test"
        else:
            command = "adb -e shell mkdir /tmp/test"
        os.system(command)
    os.makedirs(cbl_log_dir)
    log_obj.configure(log_level=log_level, plain_text=plain_text, directory=cbl_log_dir)
    log_directory = log_obj.get_directory()
    log_info("logs are enabled at: {}".format(log_directory))
    if liteserv_version < "2.5.0":
        pytest.skip('This test cannot run with CBL version below 2.5.0')

    db.create_bulk_docs(num_of_docs, id_prefix="cbl-decoder", db=cbl_db, channels=channels_sg)

    get_logs(liteserv_platform, log_directory)
    extracted_cbllog_directory_name = download_cbl_log(cbl_log_decoder_platform, liteserv_version, cbl_log_decoder_build)
    cbl_logs = os.listdir(cbl_log_dir)
    for log in cbl_logs:
        file = "{}/{}".format(cbl_log_dir, log)
        assert is_binary(file), "{} file is not binary ".format(file)
        decode_logs(extracted_cbllog_directory_name, file)


def get_logs(liteserv_platform, log_directory):
    # Not required for iOS as it stores logs in local path. Only Android and windows needs to pull logs from client
    if liteserv_platform == "android" or liteserv_platform == "xamarin-android":
        shutil.rmtree(log_directory)
        command = "adb -e pull {} {}".format(log_directory, log_directory)
        return_val = os.system(command)
        if return_val != 0:
            raise Exception("{0} failed".format(command))
    elif liteserv_platform == "net-msft" or liteserv_platform == "net-uwp":
        log_full_path = "/tmp/test"
        custom_cbl_log_dir = "c:{}".format(log_full_path)
        config_location = "resources/liteserv_configs/net-msft"
        ansible_runner = AnsibleRunner(config=config_location)

        status = ansible_runner.run_ansible_playbook(
            "fetch-only-windows-cbl-logs.yml",
            extra_vars={
                "log_full_path": log_full_path,
                "custom_cbl_log_dir": custom_cbl_log_dir
            }
        )
        if status != 0:
            raise Exception("Could not fetch cbl logs from windows ")


def download_cbl_log(cbl_log_decoder_platform, liteserv_version, cbl_log_decoder_build):

    version = liteserv_version.split('-')[0]
    if cbl_log_decoder_platform == "windows":
        package_name = "couchbase-lite-log-{}-{}-windows".format(version, cbl_log_decoder_build)
    elif cbl_log_decoder_platform == "centos" or cbl_log_decoder_platform == "ubuntu" or cbl_log_decoder_platform == "rhel" or cbl_log_decoder_platform == "debian":
        package_name = "couchbase-lite-log-{}-{}-centos".format(version, cbl_log_decoder_build)
    else:
        package_name = "couchbase-lite-log-{}-{}-macos".format(version, cbl_log_decoder_build)
    package_zip_name = "{}.zip".format(package_name)
    expected_binary_path = "{}/{}".format(BINARY_DIR, package_name)
    if os.path.isfile(expected_binary_path):
        log_info("Package is already downloaded. Skipping.")
        return

    # Package not downloaded, proceed to download from latest builds
    downloaded_package_zip_name = "{}/{}".format(BINARY_DIR, package_zip_name)
    if cbl_log_decoder_build is None:
        try:
            url = "{}/couchbase-lite-log/{}/{}".format(RELEASED_BUILDS, version, package_zip_name)
        except Exception as err:
            raise Exception(str(err) + "this version does not exist in release build, please provide cbl log decoder build number with this flag: --cbl-log-decoder-build")
    else:
        url = "{}/couchbase-lite-log/{}/{}/{}".format(LATEST_BUILDS, version, cbl_log_decoder_build, package_zip_name)

    log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, package_zip_name))
    resp = requests.get(url, verify=False)  # Need to resolve the certificate verification issue for release branch
    resp.raise_for_status()
    with open("{}/{}".format(BINARY_DIR, package_zip_name), "wb") as f:
        f.write(resp.content)
    extracted_directory_name = downloaded_package_zip_name.replace(".zip", "")
    if os.path.exists(extracted_directory_name):
        shutil.rmtree(extracted_directory_name)
    if cbl_log_decoder_platform == "macos":
        with ZipFile("{}".format(downloaded_package_zip_name), 'r') as zip_f:
            zip_f.extractall("{}".format(extracted_directory_name))
    else:
        os.system("unzip {} -d {}".format(downloaded_package_zip_name, extracted_directory_name))
    # Remove .zip
    os.remove("{}".format(downloaded_package_zip_name))
    os.chmod("{}/bin/cbl-log".format(extracted_directory_name), 0o777)
    return extracted_directory_name


def decode_logs(extracted_directory_name, file):
    output_file = "deps/binaries/cbl.txt"
    command = "{}/bin/cbl-log logcat {} {}".format(extracted_directory_name, file, output_file)
    return_val = os.system(command)
    if return_val != 0:
        raise Exception("{0} failed".format(command))
    assert not is_binary(output_file), "{} decoded file is still in binary".format(file)


def is_binary(filename):
    """Return true if the given filename is binary.
    @raise EnvironmentError: if the file does not exist or cannot be accessed.
    """
    fin = open(filename, 'rb')
    try:
        CHUNKSIZE = 1024
        while 1:
            chunk = fin.read(CHUNKSIZE)
            if b'\0' in chunk:  # found null byte
                return True
            if len(chunk) < CHUNKSIZE:
                break  # done
    finally:
        fin.close()

    return False
