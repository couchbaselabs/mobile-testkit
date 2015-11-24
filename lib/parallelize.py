import concurrent.futures
from lib import settings
import copy_reg
import types
import logging
log = logging.getLogger('test_framework')


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
                    print future.result()
                #log.info(output)
                except Exception as exception:
                    print('Generated an exception : %s : %s' % (obj, exception))

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
                    #log.info("%s method %s output %s" % (obj, method, result[obj]))
                except Exception as exception:
                    log.info('Generated an exception : %s : %s' % (obj, exception))
    return result


