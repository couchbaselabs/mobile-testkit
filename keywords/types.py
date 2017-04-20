def verify_is_list(obj):
    if type(obj) != list:
        raise TypeError("{} must be a 'list'".format(obj))


def verify_is_callable(obj):
    if not callable(obj):
        raise TypeError("{} must be a callable function".format(obj))
