from keywords import types


class UserInfo:

    def __init__(self, name, password, channels, roles):
        self.name = name
        self.password = password

        types.verify_is_list(channels)
        self.channels = channels

        types.verify_is_list(roles)
        self.roles = roles
