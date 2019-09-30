# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request

from guilang.description import Description
from guilang.description import Part
from hapic import HapicData
from rolling.kernel import Kernel
from rolling.model.build import DescribeBuildInputPath
from rolling.server.controller.base import BaseController
from rolling.server.controller.url import DESCRIBE_BUILD
from rolling.server.extension import hapic


class BuildController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)
        self._kernel = kernel

    @hapic.with_api_doc()
    @hapic.input_path(DescribeBuildInputPath)
    @hapic.output_body(Description)
    async def _describe(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO BS 2019-09-30: check current char and near this build
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        build_doc = self._kernel.build_lib.get_build_doc(hapic_data.path.build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        character_actions = self._kernel.build_lib.get_on_build_actions(
            character, hapic_data.path.build_id
        )

        return Description(
            title=f"{build_description.name}",
            items=[
                Part(text=action.get_as_str(), form_action=action.link, is_link=True)
                for action in character_actions
            ],
        )

    def bind(self, app: Application) -> None:
        app.add_routes([web.post(DESCRIBE_BUILD, self._describe)])
