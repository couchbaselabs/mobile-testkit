from MemoryPointer import MemoryPointer
from keywords.utils import log_info


class ValueSerializer:
    @staticmethod
    def serialize(value):
        if isinstance(value, MemoryPointer):
            return value.getAddress()
        elif isinstance(value, str):
            string = str(value)

            return "\"" + string + "\""
        elif isinstance(value, int):
            number = int(value)

            return str(number)
        elif isinstance(value, bool):
            bool_val = bool(value)

            return "true" if bool_val else "false"
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
        elif value.startswith("\"") and value.endswith("\""):
            return value[1:-1]
        else:
            if "." in value:
                return float(value)
            else:
                return int(value)
