# import os
# import time
# import warnings
# from logging import Logger
# from typing import Dict, Type
#
# from langchain import OpenAI
#
# from ghoshell.container import Provider, Container, Contract
# from ghoshell.llms.contracts import LLMTextCompletion
#
#
# class LangChainLLMAdapter(LLMTextCompletion):
#     """
#     测试专用, 用 langchain 减少开发成本.
#     Deprecated
#     """
#
#     def __init__(self, lc_openai: OpenAI, logger: Logger):
#         warnings.warn("deprecated: langchain adapter is test only")
#         self.lc_openai = lc_openai
#         self.logger = logger
#         self.adapters: Dict[str, LLMTextCompletion] = {}
#
#     def text_completion(self, prompt: str, config_name: str = "") -> str:
#         self.logger.debug(f"prompt: >>> {prompt}")
#         resp = self.lc_openai(prompt)
#         self.logger.debug(f"prompt resp: >>> {resp}")
#         # 避免高并发
#         time.sleep(0.1)
#         return resp
#
#
# class LangChainTestLLMAdapterProvider(Provider):
#
#     def singleton(self) -> bool:
#         return True
#
#     def contract(self) -> Type[Contract]:
#         return LLMTextCompletion
#
#     def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
#         # todo: 回头根据命名可以进行不同的设置.
#         proxy = os.environ.get("OPENAI_PROXY", None)
#         ai = OpenAI(
#             request_timeout=30,
#             max_tokens=512,
#             model_name="text-davinci-003",
#             max_retries=0,
#             openai_proxy=proxy,
#         )
#         logger = con.force_fetch(Logger)
#         # 暂时没有时间做复杂参数.
#         return LangChainLLMAdapter(ai, logger)
