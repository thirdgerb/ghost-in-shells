from ghoshell.utils import import_module_value


def test_import_module_value():
    got = import_module_value("ghoshell.utils:import_module_value")
    assert got is import_module_value
