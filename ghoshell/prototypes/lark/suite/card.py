from abc import ABCMeta, abstractmethod

from pydantic import BaseModel


class CardArgument(BaseModel, metaclass=ABCMeta):
    pass


class CardCallback(BaseModel):
    pass


class CardManager(metaclass=ABCMeta):

    @abstractmethod
    def issue(
            self,
            args: CardArgument
    ) -> None:
        pass

    @abstractmethod
    def update(
            self,
            args: CardArgument
    ) -> None:
        pass
