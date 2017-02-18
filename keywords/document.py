import logging
import base64
import uuid
import zlib

from constants import DATA_DIR
from keywords import types
from keywords import utils

import keywords.exceptions


NUM_VBUCKETS = 1024


def get_vbucket_number(key):
    """ Return the vbucket number for a given key.
        Taken from https://github.com/abhinavdangeti/cbTools/blob/f51f80b1eec5993a99fe49b45631e880b6835dc8/targetKeys.py#L6
    """
    return (((zlib.crc32(key)) >> 16) & 0x7fff) & (NUM_VBUCKETS - 1)


def generate_doc_id_for_vbucket(vbucket_number):
    """ Returns a random doc id that will hash to a given vbucket. """
    if vbucket_number < 0 or vbucket_number > 1023:
        raise keywords.exceptions.DocumentError("'vbucket_number' must be between 0-1023")

    # loop over random generated doc ids until the desired vbucket is returned
    while True:
        doc_id = str(uuid.uuid4())
        if get_vbucket_number(doc_id) == vbucket_number:
            utils.log_info("doc_id: {} -> vBucket: {}".format(doc_id, vbucket_number))
            return doc_id


def generate_doc_ids_for_vbucket(vbucket_number, number_doc_ids):
    """ Returns a list of generated doc ids that will hash to a given vBucket number """

    doc_ids = []
    for _ in range(number_doc_ids):
        doc_ids.append(generate_doc_id_for_vbucket(vbucket_number))

    return doc_ids


def get_attachment(name):
    with open("{}/{}".format(DATA_DIR, name)) as f:
        result = base64.standard_b64encode(f.read())
    return result


def create_doc(doc_id, content=None, attachment_name=None, expiry=None, channels=None):
    """
    Keyword that creates a document body as a list for use with Add Doc keyword
    return result format:
    {'channels': [u'NBC', u'ABC'], '_id': 'exp_3_0', '_exp': 3}
    """

    if channels is None:
        channels = []

    types.verify_is_list(channels)

    doc = {}

    if id is not None:
        doc["_id"] = doc_id

    if expiry is not None:
        doc["_exp"] = expiry

    if content is not None:
        doc["content"] = content

    doc["channels"] = channels

    if attachment_name is not None:
        doc["_attachments"] = {
            attachment_name: {"data": get_attachment(attachment_name)}
        }

    logging.debug(doc)

    return doc


def create_docs(doc_id_prefix, number, content=None, attachment_name=None, expiry=None, channels=None):
    """
    Keyword that creates a list of document bodies as a list for use with Add Bulk Docs keyword
    return result format:
    [
        {'channels': [u'NBC', u'ABC'], '_id': 'exp_3_0', '_exp': 3},
        {'channels': [u'NBC', u'ABC'], '_id': 'exp_3_1', '_exp': 3}, ...
    ]
    """

    if channels is None:
        channels = []

    types.verify_is_list(channels)

    docs = []

    for i in range(number):

        if doc_id_prefix is None:
            doc_id = str(uuid.uuid4())
        else:
            doc_id = "{}_{}".format(doc_id_prefix, i)

        doc = create_doc(doc_id, content, attachment_name, expiry, channels)
        docs.append(doc)

    return docs
