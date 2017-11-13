
class MemoryPointer:
    _address = None

    def __init__(self, address):
        self._address = address

    def getAddress(self):
        return self._address
