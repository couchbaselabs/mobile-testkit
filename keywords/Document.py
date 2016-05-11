import logging
import base64

from constants import *

class Document:

    def create_doc(self, id, content, attachment=None):
        doc = {}
        if id is not None:
            doc["_id"] = id
        doc["content"] = content

        if attachment is not None:
            with open ("{}/{}".format(DATA_DIR, attachment)) as f:
                doc["_attachments"] = {
                    attachment: { "data": base64.standard_b64encode(f.read()) }
                }

        logging.debug(doc)

        return doc