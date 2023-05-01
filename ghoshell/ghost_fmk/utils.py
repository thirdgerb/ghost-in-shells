from typing import ClassVar, Dict


class InstanceCount:
    count: ClassVar[Dict[str, int]] = {}

    @classmethod
    def add(cls, class_name: str):
        count = cls.count.get(class_name, 0)
        cls.count[class_name] = count + 1

    @classmethod
    def rm(cls, class_name: str):
        count = cls.count.get(class_name, 0)
        if count:
            cls.count[class_name] = count - 1




