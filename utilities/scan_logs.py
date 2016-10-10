from keywords.utils import log_info
from keywords.utils import log_error


def scan_for_errors(error_strings, log_file_path):
    """
    Scans a log file line by line for a provided array of words.
    We use this to look for errors, so we expect that no words will be found
    If any of the words are found, we raise an exception.

    'error_strings' should be a list. Example ['panic', 'error']
    """

    if type(error_strings) != list:
        raise ValueError("'error_strings must be a list'")

    log_info("Looking for {} in {} ...".format(error_strings, log_file_path))

    # Scan each line in the log file for the words to search for
    with open(log_file_path, 'r') as f:
        for line in f:
            for word in error_strings:
                # convert the word to lowercase and the line to all lower case
                # which handles the case where 'warning' will catch 'WARNING' and 'Warning', etc
                if word.lower() in line.lower():
                    log_error(line)
                    raise AssertionError("{} found!! Please review: {} ".format(word, log_file_path))

    # No errors found
    log_info("Scan complete. Did not find any error strings.")
