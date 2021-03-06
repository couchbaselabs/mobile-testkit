import json
from CBLClient.MemoryPointer import MemoryPointer


class ValueSerializer(object):
    @staticmethod
    def serialize(value):
        if value is None or value == "None":
            return "null"
        elif isinstance(value, MemoryPointer):
            return value.getAddress()
        elif isinstance(value, str):
            if value.endswith(",LONGTYPE"):
                value = value.split(',')
                return "L" + value[0]
            else:
                string = str(value)
            return "\"" + string + "\""
        elif isinstance(value, str):
            value = value.encode('utf-8')
            return "\"" + value + "\""
        elif isinstance(value, bool):
            # bool has to be before int,
            # Python's Bool gets caught by int
            bool_val = bool(value)
            return "true" if bool_val else "false"
        elif isinstance(value, int):
            if value < 1000000 and value > -1000000:
                number = int(value)
                return "I" + str(number)
            return "L" + str(value)
        elif isinstance(value, float):
            number = float(value)
            return "F" + str(number)
        # There is no double/number in python
        elif isinstance(value, dict):
            dict_map = value
            string_map = {}
            for map_param in dict_map:
                if isinstance(dict_map[map_param], bytes):
                    map_param_value = dict_map[map_param].decode()
                else:
                    map_param_value = dict_map[map_param]
                val = ValueSerializer.serialize(map_param_value)
                string_map[map_param] = val

            return json.dumps(string_map)
        elif isinstance(value, list):
            string_list = []

            for obj in value:
                string = ValueSerializer.serialize(obj)
                string_list.append(string)
            return json.dumps(string_list)

        raise RuntimeError("Invalid value type: {}: {}".format(value, type(value)))

    @staticmethod
    def deserialize(value):
        if not value or len(value) == 0 or value == "null":
            return None
        elif value.startswith("PK"):
            return value
        elif value.startswith("@") or value.startswith("\"@"):
            return MemoryPointer(value)
        elif value.startswith("\"") and value.endswith("\""):
            return value[1:-1]
        elif value == "true":
            return True
        elif value == "false":
            return False
        elif value.startswith("I") or value.startswith("L"):
            return int(value[1:])
        elif value.startswith("F") or value.startswith("D"):
            return float(value[1:])
        elif value.startswith("#"):
            if "." in value:
                return float(value[1:])
            else:
                return int(value[1:])
        elif value.startswith("{"):
            string_map = json.loads(value)
            map = {}

            for entry in string_map:
                key = str(entry)
                obj = ValueSerializer.deserialize(string_map[key])

                map[key] = obj

            return map
        elif value.startswith("["):
            string_list = json.loads(value)
            res_list = []

            for string in string_list:
                obj = ValueSerializer.deserialize(string)
                res_list.append(obj)

            return res_list

        raise RuntimeError("Invalid value type: {}: {}".format(value, type(value)))
