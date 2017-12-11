import json

from MemoryPointer import MemoryPointer


class ValueSerializer:
    @staticmethod
    def serialize(value):
        if isinstance(value, MemoryPointer):
            return value.getAddress()
        elif isinstance(value, str):
            string = str(value)
            return "\"" + string + "\""
        elif isinstance(value, bool):
            bool_val = bool(value)
            return "true" if bool_val else "false"
        elif isinstance(value, int):
            number = int(value)
            return str(number)
        elif isinstance(value, dict):
            map = value
            stringMap = {}

            for map_param in map:
                val = ValueSerializer.serialize(map[map_param])
                stringMap[map_param] = val

            return json.dumps(stringMap)
            # return json.dumps(value)
        elif isinstance(value, list):
            stringList = []

            for object in value:
                string = ValueSerializer.serialize(object)
                stringList.append(string)

            return json.dumps(stringList)
        else:
            raise Exception("Invalid value type: {}".format(value))

    @staticmethod
    def deserialize(value):
        if isinstance(value, dict):
            return value
        elif not value or len(value) == 0 or value == "null":
            return None
        elif value.startswith("@"):
            return MemoryPointer(value)
        elif value == "true":
            return True
        elif value == "false":
            return False
        elif value.startswith("\"") and value.endswith("\""):
            return value[1:-1]
        elif value.startswith("{"):
            stringMap = json.loads(value)
            map = {}

            for entry in stringMap:
                key = str(entry)
                object = ValueSerializer.deserialize(stringMap[key])

                map[key] = object

            return map
        elif value.startswith("["):
            stringList = json.loads(value)
            list = []

            for string in stringList:
                object = ValueSerializer.deserialize(string)
                list.append(object)

            return list
        else:
            if "." in value:
                return float(value)
            else:
                return int(value)
