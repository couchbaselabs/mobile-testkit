import json


class Data:

    @staticmethod
    def load(filename):
        with open("data/{}".format(filename), "r") as f:
            data = json.loads(f.read())
        return data
