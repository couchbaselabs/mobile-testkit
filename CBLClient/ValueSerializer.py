import json

from MemoryPointer import MemoryPointer

class ValueSerializer:
    @staticmethod
    def serialize(value):
        if value == None:
            return "null"
        elif isinstance(value, MemoryPointer):
            return value.getAddress()
        elif isinstance(value, str):
            return "\"" + value + "\""
        elif isinstance(value, bool):
            bool_val = bool(value)
            return "true" if bool_val else "false"
        elif isinstance(value, int):
            number = int(value)
            return str(number)
        elif isinstance(value, list):
            vallist = []
            for item in value:
                vallist.append(ValueSerializer.serialize(item))
            return json.dumps(vallist)
        elif isinstance(value, dict):
            return json.dumps(value)
        else:
            raise Exception("Invalid value type: {}".format(value))

    @staticmethod
    def deserialize(value):
        if not value or len(value) == 0 or value == "null":
            return None
        elif value.startswith("@"):
            return MemoryPointer(value)
        elif value == "true":
            return True
        elif value == "false":
            return False
        elif value.startswith("\""):
            return value[1:-1]
        elif value.startswith("{") and value.endswith("}"):
            servalue = json.loads(value)
            deserdict = {}
            for key in servalue:
                deserdict[str(key)] = ValueSerializer.deserialize(servalue[key])
            return deserdict
        elif value.startswith("[") and value.endswith("]"):
            serlist = json.loads(value)
            deserlist = []
            for item in serlist:
                deserval = ValueSerializer.deserialize(item)
                deserlist.append(deserval)
            return deserlist
        else:
            if value.isdigit():
                return int(value)
            else:
                return float(value)
