import json

from MemoryPointer import MemoryPointer


class ValueSerializer:
    @staticmethod
    def serialize(value):
        if not value:
            return "null"
        elif isinstance(value, MemoryPointer):
            return value.getAddress()
        elif isinstance(value, str):
            string = str(value)
            return "\"" + string + "\""
        elif isinstance(value, bool):
            # bool has to be before int, 
            # Python's Bool gets caught by int
            bool_val = bool(value)
            return "true" if bool_val else "false"
        elif isinstance(value, int):
            number = int(value)
            return "I" + str(number)
        elif isinstance(value, float):
            number = float(value)
            return "F" + str(number)
        elif isinstance(value, long):
            number = long(value)
            return "L" + str(number)
        elif isinstance(value, unicode):
            value = value.encode('utf-8')
            return "\"" + value + "\""
        # There is no double/number in python
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

        raise RuntimeError("Invalid value type: {}: {}".format(value, type(value)))

    @staticmethod
    def deserialize(value):
        if not value or len(value) == 0 or value == "null":
            return None
        elif value.startswith("@"):
            return MemoryPointer(value)
        elif value.startswith("\"") and value.endswith("\""):
            return value[1:-1]
        elif value.startswith("I"):
            return int(value[1:])
        elif value.startswith("L"):
            return long(value[1:])
        elif value.startswith("F") or value.startswith("D"):
            return float(value[1:])
        elif value.startswith("#"):
            if "." in value:
                return float(value[1:])
            else:
                return int(value[1:])
        elif value == "true":
            return True
        elif value == "false":
            return False
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

        raise RuntimeError("Invalid value type: {}: {}".format(value, type(value)))
