# coding: utf-8
from rolling.client.http.client import HttpClient
from rolling.kernel import Kernel


class WorldLib:
    def __init__(self, kernel: Kernel, client: HttpClient):
        self._kernel = kernel
        self._client = client

    def get_world_source(self) -> str:
        return self._client.get_world_source()
