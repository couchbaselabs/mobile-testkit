from enum import Enum

BINARY_DIR = "deps/binaries"
LATEST_BUILDS = "http://latestbuilds.hq.couchbase.com"
RESULTS_DIR = "results"

MAX_RETRIES = 5

CLIENT_REQUEST_TIMEOUT = 30

class ServerType(Enum):
    syncgateway = "syncgateway"
    listener = "listener"
