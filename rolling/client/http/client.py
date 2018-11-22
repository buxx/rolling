# coding: utf-8


class HttpClient(object):
    def __init__(self, server_address: str) -> None:
        self._server_address = server_address
