import abc


class Event(metaclass=abc.ABCMeta):
    pass


class Scope(metaclass=abc.ABCMeta):
    pass


class Context(metaclass=abc.ABCMeta):
    event: Event
    scope: Scope


class Mind(metaclass=abc.ABCMeta):
    pass


class Featuring(metaclass=abc.ABCMeta):
    pass


class Memory(metaclass=abc.ABCMeta):
    pass


class Ghost(metaclass=abc.ABCMeta):
    mind: Mind
