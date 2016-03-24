import concurrent
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from testkit.listener import Listener

from testkit import settings

import logging
log = logging.getLogger(settings.LOGGER)


def create_listener(target, local_port, apk_path, activity, reinstall):
    return Listener(target=target, local_port=local_port, apk_path=apk_path, activity=activity, reinstall=reinstall)


def parallel_install(device_defs, should_reinstall):

    listeners = {}
     # Create all listeners concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(device_defs)) as executor:

        future_to_device_name = {
            executor.submit(
                create_listener,
                target=device_def["target"],
                local_port=device_def["local_port"],
                apk_path=device_def["apk_path"],
                activity=device_def["activity"],
                reinstall=should_reinstall,
            ): device_def["target"]
            for device_def in device_defs
        }

        for future in concurrent.futures.as_completed(future_to_device_name):

            name = future_to_device_name[future]
            listener = future.result()

            listeners[name] = listener
            log.info("Listener created: {} {}".format(name, listener))

    return listeners