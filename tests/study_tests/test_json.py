import json


def test_json_loads_dict():
    e = None
    string = "[1, 2, 3]"
    try:
        loads = json.loads(string, cls=dict)
    except AttributeError as ex:
        e = ex

    assert e is not None
