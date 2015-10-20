import uuid
import json

class Data:

   #def __init__(self):

    def doc_with_channels(channels, body):
        doc_name = uuid.uuid4()
        doc = {
            "channels": channels,
            "body": body
        }
        return doc_name, doc


class Document:

    def __init__(self, channels, body):
        self.name = uuid.uuid4()
        self.channels = channels
        self.body = body

    def name_and_body(self):
        doc = {"channels": self.channels, "body": self.body}
        return str(self.name), doc

    def name_with_body(self):
        doc = {"_id": str(self.name), "channels": self.channels, "body": self.body}
        return doc
