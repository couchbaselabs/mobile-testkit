
class Args(object):
    def __init__(self):
        self.index = 0
        self._args = {}

    def setMemoryPointer(self, name, memory_pointer):
        self._args[name] = memory_pointer

    def setString(self, name, string):
        self._args[name] = str(string)

    def setInt(self, name, integer):
        self._args[name] = integer

    def setLong(self, name, long_val):
        self._args[name] = long_val

    def setFloat(self, name, f):
        self._args[name] = f

    # There is no double/number in python

    def setNumber(self, name, number):
        self._args[name] = number

    def setBoolean(self, name, bool_val):
        self._args[name] = bool_val

    def setDictionary(self, name, dictionary):
        self._args[name] = dictionary

    def setArray(self, name, array):
        self._args[name] = array

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

        key = key_args[self.index]
        val = val_args[self.index]
        self.index += 1
        return key, val
