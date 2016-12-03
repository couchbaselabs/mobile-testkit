class LiteServError(Exception):
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
