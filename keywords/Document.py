import logging
import base64

from constants import *

def get_attachment(name):
    with open("{}/{}".format(DATA_DIR, name)) as f:
         result = base64.standard_b64encode(f.read())
    return result

class Document:

    def create_doc(self, id, content=None, attachment_name=None, channels=[]):

        if not isinstance(channels, list):
            raise ValueError("channels must be of type 'list'")

        doc = {}

        if id is not None:
            doc["_id"] = id

        if content is not None:
            doc["content"] = content

        doc["channels"] = channels

        if attachment_name is not None:
            doc["_attachments"] = {
                attachment_name: { "data": get_attachment(attachment_name) }
            }

        logging.debug(doc)

        return doc
