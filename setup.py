from setuptools import setup, find_packages

test_require = ["pytest", "aioresponses", "pytest-aiohttp"]
dev_require = ["black", "isort", "pip-utils", "mypy"] + test_require

setup(
    name="rolling",
    version="0.8.3",
    description="Role game engine",
    author="Bastien Sevajol",
    author_email="sevajol.bastien@gmail.com",
    url="https://github.com/buxx/rolling",
    packages=find_packages(),
    include_package_data=True,
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
