# coding: utf-8
from setuptools import setup, find_packages

test_require = ["pytest", "aioresponses"]
dev_require = ["black", "isort", "pip-utils", "mypy"] + test_require

setup(
    name="rolling",
    version="0.1",
    description="Role game engine",
    author="Bastien Sevajol",
    author_email="sevajol.bastien@gmail.com",
    url="https://github.com/buxx/rolling",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["urwid", "aiohttp==3.5.0a1", "serpyco==0.18.2", "hapic[serpyco]", "sqlalchemy", "requests", "toml", "Pillow",
                      'click'],
    extras_require={"dev": dev_require, "test": test_require},
    entry_points={
        "console_scripts": [
            "rolling-gui=rolling.gui.run:main",
            "rolling-server=rolling.server.run:main",
            "rolling-server-turn=rolling.server.turn:main",
            "rolling-server-manage=rolling.server.manage:main",
            "rolling-generate=rolling.map.generator.run:main",
            "view256=rolling.gui.view256:main",
        ]
    },
)
