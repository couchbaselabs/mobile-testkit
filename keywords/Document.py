import logging
import base64

from constants import *

def get_attachment(name):
    with open("{}/{}".format(DATA_DIR, name)) as f:
         result = base64.standard_b64encode(f.read())
    return result

class Document:

    def create_doc(self, id, content=None, attachment=None, channels=[]):

        if not isinstance(channels, list):
            raise ValueError("channels must be of type 'list'")

        doc = {}

        if id is not None:
            doc["_id"] = id

        if content is not None:
            doc["content"] = content

        doc["channels"] = channels

        if attachment is not None:
            doc["_attachments"] = {
                attachment: { "data": get_attachment(attachment) }
            }

        logging.debug(doc)

        return doc
