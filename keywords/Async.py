from uuid import uuid4
import time
from robot.libraries.BuiltIn import BuiltIn
from robot.running.context import EXECUTION_CONTEXTS
from robot.model import Keyword

from robot.api.logger import console
from concurrent.futures import ThreadPoolExecutor

from TKClient import TKClient

# def test_func(text, seconds):
#     time.sleep(seconds)
#     return text


def method_instance_for_keyword_name(keyword_name):

    robot_libraries = BuiltIn().get_library_instance(all=True)

    for lib in robot_libraries:
        methods = [method for method in dir(robot_libraries[lib])]
        if keyword_name in methods:
            return getattr(robot_libraries[lib], method)

class Async:
    def __init__(self):
        self._futures = {}
        self.executor = ThreadPoolExecutor(max_workers=10)

    def start_async(self, keyword, *args, **kwargs):
        console(keyword)
        handle = uuid4()

        # Reso
        keyword_name_to_find = keyword.replace(" ", "_")
        method = method_instance_for_keyword_name(keyword_name_to_find)

        self._futures[handle] = self.executor.submit(method, *args, **kwargs)
        return handle

    def get_async(self, handle):
        result = self._futures[handle].result()
        return result