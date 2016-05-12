import logging
import base64

from constants import *

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
            with open ("{}/{}".format(DATA_DIR, attachment)) as f:
                doc["_attachments"] = {
                    attachment: { "data": base64.standard_b64encode(f.read()) }
                }

        logging.debug(doc)

        return doc