
# the timeout for HTTP Requests, in seconds
HTTP_REQ_TIMEOUT = 30

# Number of thread workers for requests
MAX_REQUEST_WORKERS = 100

# Backoff factor, double for each retry. in seconds
BACKOFF_FACTOR = 0.2

# HTTP request retries
MAX_HTTP_RETRIES = 9

# HTTP Retry error codes
ERROR_CODE_LIST = [500, 503]

# Log Levels:
# CRITICAL 50
# ERROR	   40
# WARNING  30
# INFO     20
# DEBUG    10
# NOTSET    0
LOG_LEVEL = 20

# Logger Name
LOGGER = 'test_framework'

# Log filename
LOG_FILE = 'test-framework.log'