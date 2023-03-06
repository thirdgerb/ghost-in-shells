from typing import Dict, TypeVar

OBJECT_T = TypeVar('OBJECT_T', bound=object)


def dict2object(data: Dict, obj: OBJECT_T) -> OBJECT_T:
    for key in data:
        if not (isinstance(key, str) and hasattr(obj, key)):
            continue
        value = data[key]
        if isinstance(value, dict) and isinstance(value, object):
            obj_val = getattr(obj, key)
            value = dict2object(value, obj_val)
        setattr(obj, key, value)
    return obj
