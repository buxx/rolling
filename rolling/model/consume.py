# coding: utf-8
import abc


class Consumeable(abc.ABC):
    @abc.abstractmethod
    def consume(self) -> None:
        pass
