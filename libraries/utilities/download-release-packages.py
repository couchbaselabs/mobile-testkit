import os
import requests
import shutil
import tarfile
import subprocess
from zipfile import ZipFile


def version_and_build(full_version):
    version_parts = full_version.split("-")
    assert len(version_parts) == 2
    return version_parts[0], version_parts[1]


def pull_package_and_dump_contents(package_defs):

    # Android sample url - http://latestbuilds.hq.couchbase.com/couchbase-lite-android/release/1.2.1/1.2.1-6/couchbase-lite-android-1.2.1-android_enterprise.zip
    # Java sample url - http://latestbuilds.hq.couchbase.com/couchbase-lite-java/release/1.2.1/1.2.1-6/couchbase-lite-java-1.2.1-enterprise.zip
    # Mac sample url - http://latestbuilds.hq.couchbase.com/couchbase-lite-ios/1.2.1/macosx/1.2.1-10/couchbase-lite-macosx-enterprise_1.2.1-10.zip
    # iOS sample url - http://latestbuilds.hq.couchbase.com/couchbase-lite-ios/1.2.1/ios/1.2.1-10/couchbase-lite-ios-enterprise_1.2.1-10.zip
    # tvOS sample url - http://latestbuilds.hq.couchbase.com/couchbase-lite-ios/1.2.1/tvos/1.2.1-10/couchbase-lite-tvos-enterprise_1.2.1-10.zip
    # sync_gateway sample url - http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/1.2.1/1.2.1-4/couchbase-sync-gateway-enterprise_1.2.1-4_x86_64.tar.gz
    # accel sample url -     http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/1.2.1/1.2.1-4/couchbase-sg-accel-enterprise_1.2.1-4_x86_64.tar.gz

    base_url = "http://latestbuilds.hq.couchbase.com"
    print("Base url: {}".format(base_url))

    package_dir = "deps/packages/"
    print("Package download directory: {}".format(package_dir))

    if os.path.isdir(package_dir):
        # Remove existing package directory
        shutil.rmtree("deps/packages/")

    os.mkdir("deps/packages")
    os.mkdir("deps/packages/package-contents")

    for platform, full_version in package_defs.iteritems():

        print("Platform: {}, Version: {}".format(platform, full_version))

        if platform == "android":
            version, build = version_and_build(full_version)
            file_name = "couchbase-lite-android-{}-android_enterprise.zip".format(version)
            extracted_file_name = "couchbase-lite-android-{}".format(version)
            url = "{}/couchbase-lite-android/release/{}/{}/{}".format(base_url, version, full_version, file_name)
        elif platform == "java":
            version, build = version_and_build(full_version)
            file_name = "couchbase-lite-java-{}-enterprise.zip".format(version)
            extracted_file_name = "couchbase-lite-java-{}".format(version)
            url = "{}/couchbase-lite-java/release/{}/{}/{}".format(base_url, version, full_version, file_name)
        elif platform == "mac":
            version, build = version_and_build(full_version)
            file_name = "couchbase-lite-macosx-enterprise_{}.zip".format(full_version)
            extracted_file_name = "couchbase-lite-macosx-{}".format(full_version)
            url = "{}/couchbase-lite-ios/{}/macosx/{}/{}".format(base_url, version, full_version, file_name)
        elif platform == "ios":
            version, build = version_and_build(full_version)
            file_name = "couchbase-lite-ios-enterprise_{}.zip".format(full_version)
            extracted_file_name = "couchbase-lite-ios-{}".format(full_version)
            url = "{}/couchbase-lite-ios/{}/ios/{}/{}".format(base_url, version, full_version, file_name)
        elif platform == "tvos":
            version, build = version_and_build(full_version)
            file_name = "couchbase-lite-tvos-enterprise_{}.zip".format(full_version)
            extracted_file_name = "couchbase-lite-tvos-{}".format(full_version)
            url = "{}/couchbase-lite-ios/{}/tvos/{}/{}".format(base_url, version, full_version, file_name)
        elif platform == "sync_gateway":
            version, build = version_and_build(full_version)
            file_name = "couchbase-sync-gateway-enterprise_{}_x86_64.tar.gz".format(full_version)
            extracted_file_name = "couchbase-sync-gateway"
            url = "{}/couchbase-sync-gateway/{}/{}/{}".format(base_url, version, full_version, file_name)
        elif platform == "accel":
            version, build = version_and_build(full_version)
            file_name = "couchbase-sg-accel-enterprise_{}_x86_64.tar.gz".format(full_version)
            extracted_file_name = "couchbase-sg-accel"
            url = "{}/couchbase-sync-gateway/{}/{}/{}".format(base_url, version, full_version, file_name)
        else:
            raise ValueError("Unsupported platform")

        # Change to package dir
        os.chdir("deps/packages/")

        # Download the packages
        print("Downloading: {}".format(url))
        resp = requests.get(url)
        resp.raise_for_status()
        with open(file_name, "wb") as f:
            f.write(resp.content)

        # Extract the package
        if file_name.endswith(".zip"):
            with ZipFile(file_name) as zip_f:
                if platform == "android" or platform == "java":
                    # Extraction folder is created as part of the unzipping
                    zip_f.extractall()
                else:
                    zip_f.extractall(extracted_file_name)

        elif file_name.endswith(".tar.gz"):
            with tarfile.open(file_name) as tar_f:
                tar_f.extractall()

        else:
            raise ValueError("Unable to extract package: {}".format(file_name))

        # Write package contents
        file_contents = subprocess.check_output(["find", extracted_file_name])
        print("\n{}\n".format(file_contents))
        with open("package-contents/{}-package-contents.txt".format(file_name), "w") as f:
            f.write("Downloaded package: {}\n\n".format(url))
            f.write(file_contents)

        # Change back to root dir
        os.chdir("../..")


if __name__ == "__main__":
    """
    usage: python dump-release-packages.py

    This script will pull the packages defined below and save the package contents in a series of files:
     android_package-1.2.1-6.txt, java_package-1.2.1-6.txt, ...
    """

    package_defs = {
        "android": "1.2.1-6",
        "java": "1.2.1-6",
        "mac": "1.2.1-10",
        "ios": "1.2.1-10",
        "tvos": "1.2.1-10",
        "sync_gateway": "1.2.1-4",
        "accel": "1.2.1-4"
    }

    pull_package_and_dump_contents(package_defs)
