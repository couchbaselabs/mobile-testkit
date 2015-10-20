import uuid


class Doc:
    def __init__(self, body):
        self.name = uuid.uuid4()
        self.body = body

    def name_and_body(self):
        doc = {"body": self.body}
        return str(self.name), doc

    def name_with_body(self):
        doc = {"_id": str(self.name), "body": self.body}
        return doc


class ChannelDoc:

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
