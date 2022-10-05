# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from hapic import HapicData

from guilang.description import Description
from guilang.description import Part
from rolling.action.utils import get_build_description_parts
from rolling.kernel import Kernel
from rolling.model.build import (
    DescribeBuildInputPath,
    LookBuildFromQuickActionPath,
    LookBuildFromQuickActionQuery,
)
from rolling.server.controller.base import BaseController
from rolling.server.controller.url import DESCRIBE_BUILD
from rolling.server.extension import hapic
from rolling.util import quantity_to_str


class BuildController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    @hapic.with_api_doc()
    @hapic.input_path(LookBuildFromQuickActionPath)
    @hapic.input_query(LookBuildFromQuickActionQuery)
    @hapic.output_body(Description)
    async def look_build_from_quick_action(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character = self._kernel.character_lib.get_document(
            hapic_data.path.character_id
        )

        for build in self._kernel.build_lib.get_zone_build(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=hapic_data.query.zone_row_i,
            zone_col_i=hapic_data.query.zone_col_i,
        ):
            if not build.is_floor:
                build_description = self._kernel.game.config.builds[build.build_id]
                return Description(
                    title=build_description.name,
                    items=[],
                    redirect=DESCRIBE_BUILD.format(
                        character_id=hapic_data.path.character_id,
                        build_id=build.id,
                    ),
                )

        return Description(
            title="Pas de bâtiment ici",
            is_quick_error=True,
            items=[],
        )

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

        parts = []

        if build_description.abilities_if_is_on:
            parts.append(
                Part(
                    text=f"En fonctionnement: " + ("Oui" if build_doc.is_on else "Non")
                )
            )

        parts.extend(
            get_build_description_parts(
                self._kernel, build_description, include_build_parts=False
            )
        )

        carried_resources = self._kernel.resource_lib.get_stored_in_build(
            hapic_data.path.build_id
        )
        if carried_resources:
            parts.extend([Part(text="Contient des resources:")])
            for carried_resource in carried_resources:
                resource_description = self._kernel.game.config.resources[
                    carried_resource.id
                ]
                quantity_str = quantity_to_str(
                    carried_resource.quantity,
                    unit=resource_description.unit,
                    kernel=self._kernel,
                )
                parts.append(
                    Part(text=f"- {resource_description.name} ({quantity_str})")
                )

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
            title=f"{build_description.name}{on_construction}",
            illustration_name=build_description.illustration,
            items=parts,
            can_be_back_url=True,
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.post(DESCRIBE_BUILD, self._describe),
                web.post(
                    "/character/{character_id}/look-build-from-quick-action",
                    self.look_build_from_quick_action,
                ),
            ]
        )
