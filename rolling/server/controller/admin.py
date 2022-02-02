# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import aiohttp_jinja2
import datetime
import os

from rolling.game.base import Game
from rolling.kernel import Kernel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic


class AdminController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/admin/configs", self.configs),
                web.post("/admin/configs", self.configs),
                web.get("/admin/config/{name}", self.config),
                web.put("/admin/refresh/characters", self.refresh_characters),
            ]
        )

    @hapic.with_api_doc()
    async def config(self, request: Request) -> Response:
        config_folder_path = self._kernel.game.config.folder_path
        with open(os.path.join(config_folder_path, request.match_info["name"])) as file:
            file_content = file.read()
        return Response(status=200, body=file_content)

    @hapic.with_api_doc()
    @aiohttp_jinja2.template("configs.html")
    async def configs(self, request: Request) -> dict:
        config_folder_path = self._kernel.game.config.folder_path
        updated = False

        game_backups = [
            f
            for f in os.listdir(config_folder_path)
            if f.startswith("game")
            and os.path.isfile(os.path.join(config_folder_path, f))
        ]
        stuff_backups = [
            f
            for f in os.listdir(config_folder_path)
            if f.startswith("stuff")
            and os.path.isfile(os.path.join(config_folder_path, f))
        ]
        world_backups = [
            f
            for f in os.listdir(config_folder_path)
            if f.startswith("world")
            and os.path.isfile(os.path.join(config_folder_path, f))
        ]

        if request.method == "POST":
            data = await request.post()
            new_game_content = data["game_content"]
            new_stuff_content = data["stuff_content"]
            new_world_content = data["world_content"]

            with open(os.path.join(config_folder_path, "game.toml")) as game_file, open(
                os.path.join(config_folder_path, "stuff.toml")
            ) as stuff_file, open(
                os.path.join(config_folder_path, "world.toml")
            ) as world_file:
                backup_game_content = game_file.read()
                backup_stuff_content = stuff_file.read()
                backup_world_content = world_file.read()

            with open(
                os.path.join(config_folder_path, "game.toml"), "w+"
            ) as game_file, open(
                os.path.join(config_folder_path, "stuff.toml"), "w+"
            ) as stuff_file, open(
                os.path.join(config_folder_path, "world.toml"), "w+"
            ) as world_file:
                game_file.write(new_game_content)
                stuff_file.write(new_stuff_content)
                world_file.write(new_world_content)

            # try new config
            try:
                game = Game(self._kernel, config_folder_path)
            except Exception as exc:
                with open(
                    os.path.join(config_folder_path, "game.toml"), "w+"
                ) as game_file, open(
                    os.path.join(config_folder_path, "stuff.toml"), "w+"
                ) as stuff_file, open(
                    os.path.join(config_folder_path, "world.toml"), "w+"
                ) as world_file:
                    game_file.write(backup_game_content)
                    stuff_file.write(backup_stuff_content)
                    world_file.write(backup_world_content)
                return {
                    "error": str(exc),
                    "updated": updated,
                    "game_content": new_game_content,
                    "game_backups": game_backups,
                    "stuff_content": new_stuff_content,
                    "stuff_backups": stuff_backups,
                    "world_content": new_world_content,
                    "world_backups": world_backups,
                }

            backup_suffix = (
                str(datetime.datetime.utcnow())
                .replace(":", "_")
                .replace(" ", "_")
                .replace("-", "_")
            )
            with open(
                os.path.join(config_folder_path, f"game_{backup_suffix}.toml"), "w+"
            ) as game_file, open(
                os.path.join(config_folder_path, f"stuff_{backup_suffix}.toml"), "w+"
            ) as stuff_file, open(
                os.path.join(config_folder_path, f"world_{backup_suffix}.toml"), "w+"
            ) as world_file:
                game_file.write(backup_game_content)
                stuff_file.write(backup_stuff_content)
                world_file.write(backup_world_content)

            self._kernel._game = game
            updated = True

        with open(os.path.join(config_folder_path, "game.toml")) as game_file, open(
            os.path.join(config_folder_path, "stuff.toml")
        ) as stuff_file, open(
            os.path.join(config_folder_path, "world.toml")
        ) as world_file:
            game_content = game_file.read()
            stuff_content = stuff_file.read()
            world_content = world_file.read()
        return {
            "updated": updated,
            "game_content": game_content,
            "game_backups": game_backups,
            "stuff_content": stuff_content,
            "stuff_backups": stuff_backups,
            "world_content": world_content,
            "world_backups": world_backups,
        }

    async def refresh_characters(self, request: Request) -> Response:
        await self._kernel.refresh_characters()
        return Response(status=204)
