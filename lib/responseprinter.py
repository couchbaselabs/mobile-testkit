class ResponsePrinter:

    def __init__(self):
        self._count = 0
        self._line = ""

    def print_status(self, resp):
        if self._count != 0 and self._count % 100 == 0:
            print(self._line)
            self._line = ""

        if resp.status_code == 200 or resp.status_code == 201:
            self._line += "."
        else:
            self._line += " " + str(resp.status_code) + " "

        self._count += 1

