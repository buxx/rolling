# coding: utf-8
import os

import pytest


@pytest.fixture
def worldmapsourcea_txt() -> str:
    with open(os.path.join('tests', 'src', 'worldmapa.txt')) as f:
        return f.read()
