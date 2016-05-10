from uuid import uuid4
from robot.libraries.BuiltIn import BuiltIn
from concurrent.futures import ThreadPoolExecutor


def method_instance_for_keyword(keyword):

    # If the keywork has spaces / capitalization, make sure to convert to python method naming
    lower_case_keyword = keyword.lower()
    method_to_find = lower_case_keyword.replace(" ", "_")

    # Get references to all instantiated robot libraries (includes custom)
    robot_libraries = BuiltIn().get_library_instance(all=True)

    # Search for keyword in all loaded libraries and get the method reference if found
    for lib in robot_libraries:
        methods = [method for method in dir(robot_libraries[lib])]
        if method_to_find in methods:
            return getattr(robot_libraries[lib], method)

    raise RuntimeError("Async: could not resolve method for keyword: {}".format(keyword))

class Async:
    """ Experimental class for executing robot framework keywords asynchronously"""

    def __init__(self):
        self._futures = {}
        self.executor = ThreadPoolExecutor(max_workers=10)

    def start_async(self, keyword, *args, **kwargs):

        handle = uuid4()

        method = method_instance_for_keyword(keyword)
        self._futures[handle] = self.executor.submit(method, *args, **kwargs)

        return handle

    def get_async(self, handle):
        result = self._futures[handle].result()
        return result