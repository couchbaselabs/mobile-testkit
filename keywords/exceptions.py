class LiteServError(Exception):
    pass


class CBServerError(Exception):
    pass


class ProvisioningError(Exception):
    pass


class CollectionError(Exception):
    pass


class TimeoutException(Exception):
    pass


class Error(Exception):
    pass


class ChangesError(Error):
    pass


class RemoteCommandError(Error):
    pass


class RestError(Error):
    pass


class TimeoutError(Error):
    pass

class ChangesError(Error):
    pass
