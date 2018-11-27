# coding: utf-8
import abc

from aiohttp.web_app import Application


class BaseController(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def bind(self, app: Application) -> None:
        """
        Register road on given app
        :param app: aiohttp app
        """
