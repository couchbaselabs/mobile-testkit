import testkit.settings

from utilities.fetch_sg_logs import fetch_sync_gateway_logs

from subprocess import Popen, PIPE
import os.path

import logging
import testkit.settings
log = logging.getLogger(testkit.settings.LOGGER)


class LoggingKeywords:

    def fetch_and_analyze_logs(self):

        log.error("\n!!!!!!!!!! TEST FAILURE !!!!!!!!!!")

        zip_file_path = fetch_sync_gateway_logs("TEST-FAILURE")

        if self.detected_data_races(zip_file_path):
            log.error("Detected data races in logs: {}".format(zip_file_path))

        if self.detected_panics(zip_file_path):
            log.error("Detected panics in logs: {}".format(zip_file_path))

    def detected_data_races(self, zip_file_path):
        return self.detected_pattern("DATA RACE", zip_file_path)

    def detected_panics(self, zip_file_path):
        return self.detected_pattern("panic", zip_file_path)

    def detected_pattern(self, pattern, zip_file_path):

        if not os.path.isfile(zip_file_path):
            log.error("Can't run zipgrep, cannot find zipfile: {}".format(zip_file_path))
            return False

        process = Popen(["zipgrep", pattern, zip_file_path], stdout=PIPE)
        (output, err) = process.communicate()
        exit_code = process.wait()
        if exit_code == 0:
            log.info("Detected pattern {}: {}".format(pattern, output))
        return exit_code == 0





