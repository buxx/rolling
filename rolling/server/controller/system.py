# coding: utf-8
import dataclasses
import json
import typing
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import aiohttp_jinja2
from pathlib import Path
import pkg_resources
import serpyco
from hapic import HapicData

from guilang.description import Description
from guilang.description import Part
from rolling.kernel import Kernel
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic
from rolling.log import server_logger


version = pkg_resources.require("rolling")[0].version


@dataclasses.dataclass
class AvatarIndexPath:
    index: int = serpyco.field(cast_on_load=True)


class SystemController(BaseController):
    def __init__(
        self,
        kernel: Kernel,
        serve_static_files: typing.Optional[str] = None,
    ) -> None:
        self._kernel = kernel
        self._serve_static_files = serve_static_files

    @hapic.with_api_doc()
    async def version(self, request: Request) -> Response:
        return Response(status=200, body=version)

    @aiohttp_jinja2.template("root.html")
    async def root(self, request: Request) -> dict:
        return {"title": self._kernel.server_config.name, "version": version}

    @hapic.with_api_doc()
    @aiohttp_jinja2.template("infos.html")
    async def infos(self, request: Request) -> dict:
        return {"game": self._kernel.game}

    @hapic.with_api_doc()
    @hapic.output_body(Description)
    async def describe_infos(self, request: Request) -> Description:
        return Description(
            title="Informations sur le serveur",
            items=[
                Part(
                    label="Ouvrir la page des informations gameplay (web)",
                    is_link=True,
                    is_web_browser_link=True,
                    # FIXME BS NOW: protocol
                    form_action=f"{self._kernel.server_config.base_url}/infos",
                )
            ],
        )

    @hapic.with_api_doc()
    async def loadings(self, request: Request) -> web.Response:
        return web.json_response(self._kernel.loadings_medias_names)

    @hapic.with_api_doc()
    async def illustrations_names(self, request: Request) -> web.Response:
        illustrations_names = []

        for item in self._kernel.game.config.resources.values():
            illustrations_names.append(item.illustration)

        for item in self._kernel.game.config.builds.values():
            illustrations_names.append(item.illustration)

        for item in self._kernel.game.stuff_manager.items:
            illustrations_names.append(item.illustration)

        for item in self._kernel.game.world_manager.world.zones_properties:
            illustrations_names.append(item.illustration)

        return web.json_response(list(set(filter(bool, illustrations_names))))

    @hapic.with_api_doc()
    @hapic.input_path(AvatarIndexPath)
    async def avatar(self, request: Request, hapic_data: HapicData) -> web.Response:
        index = hapic_data.path.index
        avatar_path = self._kernel.avatars_paths[index]
        with open(avatar_path, "rb") as avatar_file:
            return web.Response(
                body=avatar_file.read(),
                content_type="image/png",
            )

    def bind(self, app: Application) -> None:
        Path("game/media/bg").mkdir(parents=True, exist_ok=True)
        app.add_routes(
            [
                web.get("/system/version", self.version),
                web.post("/system/describe/infos", self.describe_infos),
                web.get("/infos", self.infos),
                web.get("/avatar/{index}", self.avatar),
                web.get("/system/loadings", self.loadings),
                web.get("/system/illustrations-names", self.illustrations_names),
            ]
        )

        if self._serve_static_files:
            server_logger.info(f"Serve static files from '{self._serve_static_files}'")
            app.add_routes(
                [
                    web.static(
                        "/static",
                        self._serve_static_files,
                        follow_symlinks=True,
                    ),
                ]
            )
        app.add_routes(
            [
                web.get("/", self.root),
                web.static("/media", "game/media"),
                web.static("/media_bg", "game/media/bg"),
            ]
        )
