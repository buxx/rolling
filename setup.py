# coding: utf-8
import sys
import os

import typing
from setuptools import find_packages


PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))


def get_required_dll_paths() -> typing.List[str]:
    dll_paths: typing.List[str] = []

    for file in os.listdir(os.path.join(PYTHON_INSTALL_DIR, "DLLs")):
        if file.endswith(".dll") and (file.startswith("libcrypto") or file.startswith("libssl")):
            dll_paths.append(os.path.join(PYTHON_INSTALL_DIR, "DLLs", file))

    return dll_paths


extra_arguments = {}
if "build" in sys.argv:
    from cx_Freeze import setup
    from cx_Freeze import Executable

    options = {
        "build_exe": {
            "packages": ["encodings", "dateutil"]
        }
    }
    base = None
    if sys.platform == "win32":
        base = "Console"
        # options["build_exe"]["include_files"] = get_required_dll_paths()
    extra_arguments = {
        "executables": [Executable("rolling-gui.py", base=base)],
        "options": options,
    }
else:
    from setuptools import setup

test_require = ["pytest", "aioresponses"]
dev_require = ["black", "isort", "pip-utils", "mypy"] + test_require
tui_require = ["urwid", "serpyco", "requests", "Pillow", "aiohttp==3.6.2",   "sqlalchemy", "toml"]
server_require = ["aiohttp==3.6.2", "serpyco", "hapic[serpyco]", "sqlalchemy", "toml", 'click']

setup(
    name="rolling",
    version="0.1",
    description="Role game engine",
    author="Bastien Sevajol",
    author_email="sevajol.bastien@gmail.com",
    url="https://github.com/buxx/rolling",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    extras_require={
        "dev": dev_require,
        "test": test_require,
        "tui": tui_require,
        "server": server_require,
    },
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
    **extra_arguments,
)
