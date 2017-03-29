import argparse
import os
import zipfile

from keywords.utils import log_info
from keywords.utils import log_error
from keywords.exceptions import LogScanningError


def gather_logs(directory):
    """ 
    1. Look for .zip files and unzip
    2. Scan for sync gateway / accel logs
    """

    log_info('Looking in {} for sync_gateway / accel logs ...'.format(directory))

    # Walk directory to get list of files
    file_names = []
    for root, dirs, files in os.walk(directory, topdown=True):
        for f in files:
            file_names.append(os.path.join(root, f))

    # Extract / remove any .zip files
    zip_files = [file_name for file_name in file_names if file_name.endswith('.zip')]
    for zip_file in zip_files:
        zip_file_extract_dir = zip_file.replace('.zip', '')
        log_info('Unzipping: {}'.format(zip_file))
        with zipfile.ZipFile(zip_file) as zf:
            zf.extractall(zip_file_extract_dir)
            os.remove(zip_file)

    # Walk directory again to get list of files now that everything has been extracted
    file_names = []
    for root, dirs, files in os.walk(directory, topdown=True):
        for f in files:
            file_names.append(os.path.join(root, f))

    # Get log files we would like to scan
    log_files = [file_name for file_name in file_names if file_name.endswith('.log')]

    # Scan the logs for panics and data races
    log_info('Scanning logs {} logs ...'.format(len(log_files)))
    issues_found = False
    for log_file in log_files:
        try:
            scan_for_errors(log_file, ['panic', 'data race'])
        except LogScanningError as lse:
            log_info(lse.message)
            issues_found = True

    if issues_found:
        raise LogScanningError('ERROR!!! Found panics or data races!!')


def scan_for_errors(log_file_path, error_strings):
    """
    Scans a log file line by line for a provided array of words.
    We use this to look for errors, so we expect that no words will be found
    If any of the words are found, we raise an exception.

    'error_strings' should be a list. Example ['panic', 'error', 'data race']
    """

    if type(error_strings) != list:
        raise ValueError('error_strings must be a list')

    # Scan each line in the log file for the words to search for
    with open(log_file_path) as f:
        for line in f:
            for word in error_strings:
                # convert the word to lowercase and the line to all lower case
                # which handles the case where 'warning' will catch 'WARNING' and 'Warning', etc
                if word.lower() in line.lower():
                    log_error(line)
                    raise LogScanningError('{} found!! Please review: {} '.format(word, log_file_path))


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--path-to-log-dir', help='Directory containing the log files', required=True)
    args = parser.parse_args()

    gather_logs(args.path_to_log_dir)
