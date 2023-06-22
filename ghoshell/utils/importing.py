import importlib


def import_module_value(module_value_path: str):
    """
    import module value by string
    """
    sections = module_value_path.split(".")
    module_path = ".".join(sections[:len(sections) - 1])
    value_name = sections[len(sections) - 1]
    module = importlib.import_module(module_path)
    return getattr(module, value_name)
