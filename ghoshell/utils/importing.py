import importlib


def import_module_value(module_value_path: str):
    """
    import module value by string
    """
    sections = module_value_path.split(":", 2)
    module_path = sections[0]
    value_name = ""
    if len(sections) == 2:
        value_name = sections[1]
    module = importlib.import_module(module_path)
    if value_name:
        return getattr(module, value_name)
    else:
        return module
