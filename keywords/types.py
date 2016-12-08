def verify_is_list(obj):
    if type(obj) != list:
        raise TypeError("{} must be a 'list'".format(obj))
