import pytest
import mimetypes
import os
import requests

from zipfile import ZipFile
from keywords.constants import BINARY_DIR
from keywords.constants import RELEASED_BUILDS
from keywords.constants import LATEST_BUILDS
from CBLClient.FileLogging import FileLogging
from keywords.utils import log_info

@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.database
@pytest.mark.parametrize("log_level, plain_text", [
    ("verbose", False),
])
def test_cbl_decoder(params_from_base_test_setup, log_level, plain_text):
    base_url = params_from_base_test_setup["base_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cbl_log_decoder_platform = params_from_base_test_setup["cbl_log_decoder_platform"]
    cbl_log_decoder_build = params_from_base_test_setup["cbl_log_decoder_build"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    log_obj = FileLogging(base_url)
    num_of_docs = 10
    channels_sg = ["ABC"]

    log_obj.configure(log_level=log_level, plain_text=plain_text)
    log_file = log_obj.get_directory()
    log_info("logs are enabled at: {}".format(log_file))
    if liteserv_version < "2.5.0":
        pytest.skip('This test cannot run with CBL version below 2.5.0')

    db.create_bulk_docs(num_of_docs, id_prefix="cbl-decoder", db=cbl_db, channels=channels_sg)

    log_dir = "resources/data/cbl_logs/xamarin-android"
    cbl_logs = os.listdir(log_dir)
    extracted_cbllog_directory_name = download_cbl_log(cbl_log_decoder_platform, liteserv_version, cbl_log_decoder_build)
    for log in cbl_logs:
        file = "{}/{}".format(log_dir, log)
        assert is_binary(file), "{} file is not binary ".format(file)
        decode_logs(extracted_cbllog_directory_name, file)


def download_cbl_log(cbl_log_decoder_platform, liteserv_version, cbl_log_decoder_build):

    version = liteserv_version.split('-')[0]
    if cbl_log_decoder_platform == "windows" :
        package_name = "couchbase-lite-log-{}-{}-windows.zip".format(version, cbl_log_decoder_build)
    elif cbl_log_decoder_platform == "centos" or cbl_log_decoder_platform == "ubuntu" or cbl_log_decoder_platform == "rhel" or cbl_log_decoder_platform == "debian":
        package_name = "couchbase-lite-log-{}-{}-centos.zip".format(version, cbl_log_decoder_build)
    else:
        package_name = "couchbase-lite-log-{}-{}-macos.zip".format(version, cbl_log_decoder_build)
    expected_binary_path = "{}/{}".format(BINARY_DIR, package_name)
    if os.path.isfile(expected_binary_path):
        log_info("Package is already downloaded. Skipping.")
        return

    # Package not downloaded, proceed to download from latest builds
    downloaded_package_zip_name = "{}/{}".format(BINARY_DIR, package_name)
    if cbl_log_decoder_build is None:
        try:
            url = "{}/couchbase-lite-log/{}/{}".format(RELEASED_BUILDS, version, package_name)
        except Exception as err:
            raise Exception(str(err) + "this version does not exist in release build, please provide cbl log decoder build number with this flag: --cbl-log-decoder-build")
    else:
        url = "{}/couchbase-lite-log/{}/{}/{}".format(LATEST_BUILDS, version, cbl_log_decoder_build, package_name)

        log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, package_name))
        resp = requests.get(url, verify=False)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, package_name), "wb") as f:
            f.write(resp.content)
        extracted_directory_name = downloaded_package_zip_name.replace(".zip", "")
        with ZipFile("{}".format(downloaded_package_zip_name)) as zip_f:
            zip_f.extractall("{}".format(extracted_directory_name))

        # Remove .zip
        os.remove("{}".format(downloaded_package_zip_name))
        os.chmod("{}/bin/cbl-log".format(extracted_directory_name), 0777)
        print("changed the permission and had full permissions")
        return extracted_directory_name


def decode_logs(extracted_directory_name, file):
    print("extracted directory name is ", extracted_directory_name)
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
            if '\0' in chunk:  # found null byte
                return True
            if len(chunk) < CHUNKSIZE:
                break  # done
    finally:
        fin.close()

    return False
