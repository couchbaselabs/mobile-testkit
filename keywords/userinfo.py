import keywords.types


class UserInfo:

    def __init__(self, name, password, channels, roles):
        self.name = name
        self.password = password

        keywords.types.verify_is_list(channels)
        self.channels = channels

        keywords.types.verify_is_list(roles)
        self.roles = roles
