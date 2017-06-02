class Error(Exception):
    pass


class LiteServError(Error):
    pass


class CBServerError(Error):
    pass


class ProvisioningError(Error):
    pass


class CollectionError(Error):
    pass


class TimeoutException(Error):
    pass


class ChangesError(Error):
    pass


class RemoteCommandError(Error):
    pass


class RestError(Error):
    pass


class TimeoutError(Error):
    pass


class ClusterError(Error):
    pass


class DocumentError(Error):
    pass


class LogScanningError(Error):
    pass
