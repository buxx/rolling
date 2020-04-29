# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from hapic import HapicData

from guilang.description import Description
from guilang.description import Part
from rolling.kernel import Kernel
from rolling.model.build import DescribeBuildInputPath
from rolling.server.controller.base import BaseController
from rolling.server.controller.url import DESCRIBE_BUILD
from rolling.server.extension import hapic
from rolling.util import quantity_to_str


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

        on_construction = ""
        if build_doc.under_construction:
            on_construction = " (en construction)"

        carried_resources = self._kernel.resource_lib.get_stored_in_build(hapic_data.path.build_id)
        carried_in = []
        for carried_resource in carried_resources:
            resource_description = self._kernel.game.config.resources[carried_resource.id]
            quantity_str = quantity_to_str(
                carried_resource.quantity, unit=resource_description.unit, kernel=self._kernel
            )
            carried_in.append(Part(text=f"- {resource_description.name} ({quantity_str})"))
        if carried_in:
            carried_in.insert(0, Part(text="Contient des resources:"))
            carried_in.insert(1, Part(text=""))
            carried_in.append(Part(text=" "))

        parts = carried_in
        parts.extend(
            [
                Part(
                    text=action.get_as_str(),
                    form_action=action.link,
                    is_link=True,
                    link_group_name=action.group_name,
                )
                for action in character_actions
            ]
        )

        return Description(
            title=f"{build_description.name}{on_construction}", items=parts, can_be_back_url=True
        )

    def bind(self, app: Application) -> None:
        app.add_routes([web.post(DESCRIBE_BUILD, self._describe)])
