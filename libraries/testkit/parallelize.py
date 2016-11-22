import concurrent.futures
from libraries.testkit import settings
import copy_reg
import types
from threading import Thread

from keywords.utils import log_info
from keywords.utils import log_debug


# This function is added to use ProcessExecutor
# concurrent.futures.
#
def _pickle_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)


copy_reg.pickle(types.MethodType, _pickle_method)


# Using Process Pool
def parallel_process(objects, method, *args):
    with concurrent.futures.ProcessPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:
        futures = {executor.submit(getattr(obj, method), *args): obj for obj in objects}
        for future in concurrent.futures.as_completed(futures):
            if concurrent.futures.as_completed(futures):
                obj = futures[future]
                try:
                    log_debug("Object {} method {} output {}".format(obj, method, future.result()))
                except Exception as exception:
                    log_info('Generated an exception : {} : {}'.format(obj, exception))


# Using Thread Pool
def in_parallel(objects, method, *args):
    result = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:
        futures = {executor.submit(getattr(obj, method), *args): obj for obj in objects}
        for future in concurrent.futures.as_completed(futures):
            if concurrent.futures.as_completed(futures):
                obj = futures[future]
                try:
                    result[obj] = future.result()
                    log_debug("Object {} method {} output {}".format(obj, method, result[obj]))
                except Exception as exception:
                    log_info('Generated an exception : {} : {}'.format(obj, exception))
                    raise ValueError('in_parallel: got exception', exception, obj)
    return result


def run_async(function, *args, **kwargs):
    thread = Thread(target=function, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
