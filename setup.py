# coding: utf-8
from setuptools import setup

test_require = ["pytest"]
dev_require = ["black", "isort", "pip-utils", "mypy"] + test_require

setup(
    name="rolling",
    version="0.1",
    description="Role game engine",
    author="Bastien Sevajol",
    author_email="sevajol.bastien@gmail.com",
    url="https://github.com/buxx/rolling",
    packages=["rolling"],
    install_requires=["urwid", "aiohttp", "serpyco", "hapic[serpyco]", "sqlalchemy", "requests"],
    extras_require={"dev": dev_require, "test": test_require},
    entry_points={
        "console_scripts": [
            "rolling=rolling.gui.run:main",
            "rolling-server=rolling.server.run:main",
            "rolling-generate=rolling.map.generator.run:main",
        ]
    },
)
