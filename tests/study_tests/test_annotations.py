# def test_class_annotations():
#
#     class ClassAnnotation:
#
#         def __init__(self, caller, bar: int):
#             self.caller = caller
#             self.bar = bar
#
#         def run(self, bar: int) -> int:
#             return self.caller(bar) + self.bar
#
#         def wrap(self, caller):
#             def fn():
#                 return self
#             return fn
#
#     class Target:
#
#         @ClassAnnotation(3).wrap()
#         def count(self, bar: int) -> int:
#             return bar + 1