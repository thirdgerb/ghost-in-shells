import importlib

__cached_module_value = {}


def import_module_value(module_value_path: str):
    if module_value_path not in __cached_module_value:
        __cached_module_value[module_value_path] = _import_module_value(module_value_path)
    return __cached_module_value.get(module_value_path)


def _import_module_value(module_value_path: str):
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
