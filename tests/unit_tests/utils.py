def get_call_arg(call_obj, name=None):
    """
    Safely get an argument from a mock call object.
    Use either `index` for positional args or `name` for keyword args.
    """
    if name is not None:
        return call_obj.kwargs.get(name)
    raise ValueError("You must specify either `index` or `name`")
