import json
import re
from jinja2 import Template

from libraries.testkit import settings
from keywords.utils import log_info

import logging
log = logging.getLogger(settings.LOGGER)


class Config:

    def __init__(self, conf_path):

        self.conf_path = conf_path
        self.mode = None
        self.bucket_name_set = []

        with open(conf_path, "r") as config:

            data = config.read()

            # Render the jinja2 template, which will strip out any
            # templated variables in {{ ... }}
            # Sync function has to be ignored for rendering
            # Check if a sync function id defined between ` `
            temp_config = ""
            if re.search('`', data):
                log_info("Ignoring the sync function to render template")
                conf = re.split('`', data)
                split_len = len(conf)

                # Replace the sync function with a string "function"
                for i in range(0, split_len, 2):
                    if i == split_len - 1:
                        temp_config += conf[i]
                    else:
                        temp_config += conf[i] + " \"syncfunction\" "

                data = temp_config

            template = Template(data)

            # In order to render the template and produce _valid json_, we need to
            # replace any JSON boolean variables with actual values.  Simply rendering
            # the template with no variables will end up with JSON that looks like:
            #
            # {
            #   ...
            #   "writer":
            # }
            #
            # which won't parse!  Note that template variables embedded in strings don't have this issue:
            #
            # "server":"http://{{ couchbase_server_primary_node }}:8091",
            #
            # There doesn't seem to be an easy way to get the list of all template variables from
            # jinja2, and so the code below just sets all template variables that are known to be
            # boolean values -- yes this is a dirty filthy hack.  And yes, when people create
            # sync gateway configs that have new JSON template values, this will completely break.
            #
            # TODO: find a better way to handle this
            data = template.render(
                is_index_writer="false",
                autoimport="",
                xattrs=""
            )

            # strip out sync functions `function ... }`
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
            self.mode = "di"
        else:
            self.mode = "cc"

    def discover_bucket_name_set(self, conf_obj):

        bucket_names_from_config = []
        # Add CBGT buckets
        if "cluster_config" in conf_obj.keys():
            bucket_names_from_config.append(conf_obj["cluster_config"]["bucket"])

        dbs = conf_obj["databases"]
        for _, val in dbs.iteritems():

            if "bucket" in val:

                # Add data buckets
                bucket_names_from_config.append(val["bucket"])
                if "channel_index" in val:
                    # index buckets
                    bucket_names_from_config.append(val["channel_index"]["bucket"])

            if "shadow" not in val:
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
