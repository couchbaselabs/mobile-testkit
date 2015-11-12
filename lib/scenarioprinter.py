import sys

class ScenarioPrinter:

    def __init__(self):
        self._request_count = 0
        self._user_count = 0
        self._changes_count = 0

        self._request_line = ""
        self._user_line = ""
        self._changes_line = ""

    def print_status(self, resp):
        if self._request_count > 100:
            print(self._request_line)
            self._request_count = 0
            self._request_line = ""

        if resp.status_code == 200 or resp.status_code == 201:
            self._request_line += '.'
        else:
            self._request_line += " {} ".format(str(resp.status_code))
        self._request_count += 1

    def print_user_add(self):
        if self._user_count > 100:
            print(self._user_line)
            self._user_count = 0
            self._user_line = ""

        self._user_line += 'u'
        self._user_count += 1

    def print_changes_num(self, user, number):
        if self._changes_count > 10:
            print(self._changes_line)
            self._changes_count = 0
            self._changes_line = ""

        self._changes_line += " {}:{} ".format(user, number)
        self._changes_count += 1



