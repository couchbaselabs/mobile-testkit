import logging
import settings

# create logger
log = logging.getLogger("test_framework")
log.setLevel(settings.LOG_LEVEL)

# create file handler which logs even debug messages
fh = logging.FileHandler(settings.LOG_FILE)
fh.setLevel(logging.DEBUG)

# create console handler and set log level
ch = logging.StreamHandler()
ch.setLevel(settings.LOG_LEVEL)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')

# add formatters
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# add handlers to logger
log.addHandler(ch)
log.addHandler(fh)