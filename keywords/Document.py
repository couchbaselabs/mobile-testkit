import logging
import base64

from constants import DATA_DIR


def get_attachment(name):
    with open("{}/{}".format(DATA_DIR, name)) as f:
        result = base64.standard_b64encode(f.read())
    return result


class Document:

    def create_doc(self, id, content=None, attachment_name=None, expiry=None, channels=[]):
        """
        Keyword that creates a document body as a list for use with Add Doc keyword
        return result format:
        {'channels': [u'NBC', u'ABC'], '_id': 'exp_3_0', '_exp': 3}
        """

        if not isinstance(channels, list):
            raise ValueError("channels must be of type 'list'")

        doc = {}

        if id is not None:
            doc["_id"] = id

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

    def create_docs(self, id_prefix, number, content=None, attachment_name=None, expiry=None, channels=[]):
        """
        Keyword that creates a list of document bodies as a list for use with Add Bulk Docs keyword
        return result format:
        [
            {'channels': [u'NBC', u'ABC'], '_id': 'exp_3_0', '_exp': 3},
            {'channels': [u'NBC', u'ABC'], '_id': 'exp_3_1', '_exp': 3}, ...
        ]
        """

        docs = []

        for i in range(number):
            doc_id = "{}_{}".format(id_prefix, i)
            doc = self.create_doc(doc_id, content, attachment_name, expiry, channels)
            docs.append(doc)

        return docs
