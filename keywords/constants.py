from enum import Enum

BINARY_DIR = "deps/binaries"
LATEST_BUILDS = "http://latestbuilds.service.couchbase.com/builds/latestbuilds"
RELEASED_BUILDS = "http://latestbuilds.service.couchbase.com/builds/releases/mobile"
RESULTS_DIR = "results"
TEST_DIR = "framework_tests"
CLUSTER_CONFIGS_DIR = "resources/cluster_configs"
SYNC_GATEWAY_CONFIGS = "resources/sync_gateway_configs"
SYNC_GATEWAY_CERT = "resources/sync_gateway_cert"
DATA_DIR = "resources/data"
ENVIRONMENT_FILE = "resources/data/environment_file.txt"

MAX_RETRIES = 10

CLIENT_REQUEST_TIMEOUT = 180
REBALANCE_TIMEOUT_SECS = 3600
REMOTE_EXECUTOR_TIMEOUT = 180
SDK_TIMEOUT = 3600

# Required to make sure that these are created with encryption
# Use to build the command line flags for encryption
REGISTERED_CLIENT_DBS = ["ls_db", "ls_db1", "ls_db2"]


class ServerType(Enum):
    syncgateway = "syncgateway"
    listener = "listener"


class Platform(Enum):
    macosx = "macosx"
    android = "android"
    net = "net"
    centos = "centos"


class AuthType(Enum):
    http_basic = "http_basic"
    session = "session"
    none = "none"
