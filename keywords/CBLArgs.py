from keywords.utils import log_info


class Args:
    _args = {}
    index = 0

    def __init__(self):
        self.index = 0

    def setMemoryPointer(self, name, memoryPointer):
        self._args[name] = memoryPointer

    def setString(self, name, string):
        self._args[name] = string

    def setInt(self, name, integer):
        self._args[name] = int(integer)

    def setNumber(self, name, number):
        self._args[name] = number

    def setBoolean(self, name, bool_val):
        self._args[name] = bool_val

    def getArgs(self):
        return self._args

    def setIndex(self, index):
        self.index = index

    def __iter__(self):
        return self

    def next(self):
        key_args = self._args.keys()
        val_args = self._args.values()

        if self.index >= len(self._args):
            self.index = 0
            raise StopIteration

        k = key_args[self.index]
        v = val_args[self.index]
        self.index += 1
        return k, v
