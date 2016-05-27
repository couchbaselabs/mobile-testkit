from enum import Enum

BINARY_DIR = "deps/binaries"
LATEST_BUILDS = "http://latestbuilds.hq.couchbase.com"
RESULTS_DIR = "results"
CLUSTER_CONFIGS_DIR = "resources/cluster_configs"
DATA_DIR = "resources/data"

MAX_RETRIES = 5

CLIENT_REQUEST_TIMEOUT = 120

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
