import os
import re
import sys
import json
import time

from testkit import settings

import logging
log = logging.getLogger(settings.LOGGER)

class Config:

    def __init__(self, conf_path):

        self.conf_path = conf_path
        self.mode = None 
        self.bucket_name_set = []
        
        with open(conf_path, "r") as config:
            data = config.read()

            # strip out templated variables {{ ... }} and sync functions `function ... }`
            data = convert_to_valid_json(data)

            # Find all bucket names in config's databases: {}
            conf_obj = json.loads(data)

            self.discover_mode(conf_obj)

            self.discover_bucket_name_set(conf_obj)


    def get_mode(self):

        return self.mode

    def get_bucket_name_set(self):

        return self.bucket_name_set

    def discover_mode(self, conf_obj):
        
        if "cluster_config" in conf_obj.keys():
            self.mode = "distributed_index"
        else:
            self.mode = "channel_cache"
        
    def discover_bucket_name_set(self, conf_obj):

            bucket_names_from_config = []
            # Add CBGT buckets
            if "cluster_config" in conf_obj.keys():
                bucket_names_from_config.append(conf_obj["cluster_config"]["bucket"])

            dbs = conf_obj["databases"]
            for key, val in dbs.iteritems():
                # Add data buckets
                bucket_names_from_config.append(val["bucket"])
                if "channel_index" in val:
                    # index buckets
                    bucket_names_from_config.append(val["channel_index"]["bucket"])

                if not val.has_key("shadow"):
                    continue

                shadow = val["shadow"]
                if len(shadow["bucket"]) > 0:
                    bucket_names_from_config.append(shadow["bucket"])

            # Buckets may be shared for different functionality
            self.bucket_name_set = list(set(bucket_names_from_config))


def convert_to_valid_json(invalid_json):

    """
    Copied and pasted from https://github.com/couchbase/sync_gateway/blob/master/tools/password_remover.py

    TODO: share common code somehow
    """

    STATE_OUTSIDE_BACKTICK = "STATE_OUTSIDE_BACKTICK"
    STATE_INSIDE_BACKTICK = "STATE_INSIDE_BACKTICK"
    state = STATE_OUTSIDE_BACKTICK
    output = []
    sync_function_buffer = []

    # Strip newlines
    invalid_json = invalid_json.replace('\n', '')

    # Strip tabs
    invalid_json = invalid_json.replace('\t', '')

    # read string char by char
    for json_char in invalid_json:

        # if non-backtick character:
        if json_char != '`':

            # if in OUTSIDE_BACKTICK state
            if state == STATE_OUTSIDE_BACKTICK:
                # append char to output
                output.append(json_char)

            # if in INSIDE_BACKTICK state
            elif state == STATE_INSIDE_BACKTICK:
                # append to sync_function_buffer
                sync_function_buffer.append(json_char)

        # if backtick character
        elif json_char == '`':

            # if in OUTSIDE_BACKTICK state
            if state == STATE_OUTSIDE_BACKTICK:
                # transition to INSIDE_BACKTICK state
                state = STATE_INSIDE_BACKTICK

            # if in INSIDE_BACKTICK state
            elif state == STATE_INSIDE_BACKTICK:
                # run sync_function_buffer through escape_json_value()
                sync_function_buffer_str = "".join(sync_function_buffer)
                sync_function_buffer_str = escape_json_value(sync_function_buffer_str)

                # append to output
                output.append('"')  # append a double quote
                output.append(sync_function_buffer_str)
                output.append('"')  # append a double quote

                # empty the sync_function_buffer
                sync_function_buffer = []

                # transition to OUTSIDE_BACKTICK state
                state = STATE_OUTSIDE_BACKTICK

    output_str = "".join(output)
    return output_str


def escape_json_value(raw_value):
    """

    Copied and pasted from https://github.com/couchbase/sync_gateway/blob/master/tools/password_remover.py

    TODO: share common code somehow

    Escape all invalid json characters like " to produce a valid json value

    Before:

    function(doc, oldDoc) {            if (doc.type == "reject_me") {

    After:

    function(doc, oldDoc) {            if (doc.type == \"reject_me\") {

    """
    escaped = raw_value
    escaped = escaped.replace('\\', "\\\\")  # Escape any backslashes
    escaped = escaped.replace('"', '\\"')    # Escape double quotes
    escaped = escaped.replace("'", "\\'")    # Escape single quotes

    # TODO: other stuff should be escaped like \n \t and other control characters
    # See http://stackoverflow.com/questions/983451/where-can-i-find-a-list-of-escape-characters-required-for-my-json-ajax-return-ty

    return escaped