import json


class Data:

    @staticmethod
    def load(filename):
        with open("resources/data/{}".format(filename), "r") as f:
            data = json.loads(f.read())
        return data
