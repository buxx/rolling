# coding: utf-8
import abc
from aiohttp.web_app import Application

from rolling.kernel import Kernel


class BaseController(metaclass=abc.ABCMeta):
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    @abc.abstractmethod
    def bind(self, app: Application) -> None:
        """
        Register road on given app
        :param app: aiohttp app
        """
