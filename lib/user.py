import base64
import json

class User:

    def __init__(self, name, password, channels):
        self.name = name
        self.password = password
        self.channels = channels
        auth = base64.b64encode("{0}:{1}".format(self.name, self.password).encode())
        self.auth = auth.decode("UTF-8")
