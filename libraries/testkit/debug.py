import logging

def log_request(request):
    logging.debug("{0} {1}\nHEADERS = {2}\nBODY = {3}".format(
            request.request.method,
            request.request.url,
            request.request.headers,
            request.request.body
        )
    )


def log_response(response):
    logging.debug("{}".format(response.text))


def log_user_request(name, request):
    logging.debug("{0} {1} {2}\nHEADERS = {3}\nBODY = {4}".format(
            name,
            request.request.method,
            request.request.url,
            request.request.headers,
            request.request.body
        )
    )
