from libraries.provision.install_couchbase_server import CouchbaseServerConfig


def test_version_only():
    server_config = CouchbaseServerConfig(
        version="4.1.1"
    )
    assert server_config.version == "4.1.1"
    assert server_config.build is None


def test_version_build():
    server_config = CouchbaseServerConfig(
        version="4.1.1-5914"
    )
    assert server_config.version == "4.1.1"
    assert server_config.build == "5914"


def test_enterprise():
    server_config = CouchbaseServerConfig(
        version="4.1.1-5914"
    )
    base_url, package_name = server_config.get_baseurl_package()
    assert base_url == "http://latestbuilds.service.couchbase.com/builds/latestbuilds/couchbase-server/sherlock/5914"
    assert package_name == "couchbase-server-enterprise-4.1.1-5914-centos7.x86_64.rpm"


def test_mobile_url():
    server_config = CouchbaseServerConfig(
        version="4.1.1"
    )
    base_url, package_name = server_config.get_baseurl_package()
    assert base_url == "http://cbmobile-packages.s3.amazonaws.com"
    assert package_name == "couchbase-server-enterprise-4.1.1-5914-centos7.x86_64.rpm"
