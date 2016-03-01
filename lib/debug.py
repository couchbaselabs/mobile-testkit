from lib import settings
import logging
log = logging.getLogger(settings.LOGGER)


def log_request(request):
    log.debug("{0} {1}\nHEADERS = {2}\nBODY = {3}".format(
            request.request.method,
            request.request.url,
            request.request.headers,
            request.request.body
        )
    )


def log_response(response):
    log.debug("{}".format(response.text))


def log_user_request(name, request):
    log.debug("{0} {1} {2}\nHEADERS = {3}\nBODY = {4}".format(
            name,
            request.request.method,
            request.request.url,
            request.request.headers,
            request.request.body
        )
    )
