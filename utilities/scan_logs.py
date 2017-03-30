import argparse
import os
import zipfile

from keywords.utils import log_info
from keywords.exceptions import LogScanningError


def get_file_paths_with_extension(directory, extension):
    """ Walk a directory recursively and return absolute file paths
    of file matching a certain extension. """

    # Walk directory to get list of files
    file_paths = []
    for root, dirs, file_names in os.walk(directory, topdown=True):
        for f in file_names:
            file_paths.append(os.path.join(root, f))
    return [file_path for file_path in file_paths if file_path.endswith(extension)]


def unzip_log_files(directory):
    """ Scan directory recursively for .zip files and unzip them to a folder with the same name """

    zip_files = get_file_paths_with_extension(directory, '.zip')
    for zip_file in zip_files:
        zip_file_extract_dir = zip_file.replace('.zip', '')
        log_info('Unzipping: {}'.format(zip_file))
        with zipfile.ZipFile(zip_file) as zf:
            zf.extractall(zip_file_extract_dir)


def scan_logs(directory):
    """ Unzips .zip files and scans directory recursively for .log files and scan them for error key words.
    Raise an exception if any of the error keywords are found.
    """
    # Unzip logs
    unzip_log_files(directory)

    log_file_paths = get_file_paths_with_extension(directory, '.log')

    found_errors = False
    for logfile_path in log_file_paths:
        try:
            scan_for_errors(logfile_path, ['panic', 'data race'])
        except LogScanningError:
            log_info('Error found for: {}'.format(logfile_path))
            found_errors = True

    if found_errors:
        raise LogScanningError('Found errors in the sync gateway / sg accel logs!!')


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
                    raise LogScanningError('{} found!! Please review: {} '.format(word, log_file_path))


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--path-to-log-dir', help='Directory containing the log files', required=True)
    args = parser.parse_args()

    # Scan all log files in the directory for 'panic' and 'data races'
    scan_logs(args.path_to_log_dir)
