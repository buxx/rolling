# coding: utf-8
import dataclasses

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from hapic import HapicData
import sqlalchemy.exc
import serpyco

from guilang.description import Description
from guilang.description import Part
from rolling.kernel import Kernel
from rolling.model.world import WorldAsCharacter
from rolling.server.controller.base import BaseController
from rolling.server.extension import hapic
from rolling.exception import ImpossibleAction


@dataclasses.dataclass
class ManageFromBuildModel:
    build_id: int = serpyco.field(cast_on_load=True)
    character_id: str = serpyco.field(cast_on_load=True)


@dataclasses.dataclass
class CreateFromBuildModel:
    build_id: int = serpyco.field(cast_on_load=True)
    affinity_id: int = serpyco.field(cast_on_load=True)
    character_id: str = serpyco.field(cast_on_load=True)


class SpawnPointController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    @hapic.with_api_doc()
    @hapic.input_path(ManageFromBuildModel)
    @hapic.output_body(Description)
    async def management_from_build(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character_id = hapic_data.path.character_id
        build_id = hapic_data.path.build_id
        description_part = Part(
            text=(
                "Un point d'apparition permet aux nouveaux personnage de choisir un "
                "endroit où apparaitre dans le monde."
            )
        )

        try:
            self._kernel.spawn_point_lib.get_from_build(build_id)
            return Description(
                title="Points d'apparition déjà utilisé",
                items=[
                    description_part,
                    Part(text=" "),
                    Part(text="Un point d'aparition est déjà activé pour ce bâtiment"),
                ],
            )
        except sqlalchemy.exc.NoResultFound:
            pass

        affinities_already_have = []
        affinities_dont_have = []
        for affinity_relation in self._kernel.affinity_lib.get_accepted_affinities(
            character_id=character_id
        ):
            affinity = self._kernel.affinity_lib.get_affinity(
                affinity_relation.affinity_id
            )
            if self._kernel.spawn_point_lib.affinity_have_spawn_point(affinity.id):
                affinities_already_have.append(affinity)
            else:
                affinities_dont_have.append(affinity)

        parts = []
        for affinity_already_have in affinities_already_have:
            parts.append(
                Part(
                    text=f"{affinity_already_have.name}: possède déjà un point d'apparition"
                )
            )
        for affinity_dont_have in affinities_dont_have:
            parts.append(
                Part(
                    is_link=True,
                    form_action=f"/spawn/{character_id}/from-build/{build_id}/create/{affinity_dont_have.id}",
                    label=f"{affinity_dont_have.name}: créer un point d'apparition",
                )
            )

        return Description(
            title="Points d'apparition",
            items=[
                description_part,
                Part(text=" "),
            ]
            + parts,
        )

    @hapic.with_api_doc()
    @hapic.input_path(CreateFromBuildModel)
    @hapic.output_body(Description)
    async def create_from_build(
        self, request: Request, hapic_data: HapicData
    ) -> Description:
        character_id = hapic_data.path.character_id
        build_id = hapic_data.path.build_id
        affinity_id = hapic_data.path.affinity_id

        if (
            not self._kernel.affinity_lib.get_chief_of_affinity(
                affinity_id
            ).character_id
            == character_id
        ):
            return Description(title="Vous devez être le chef")

        try:
            self._kernel.spawn_point_lib.check_can_create_spawn_point_with_build(
                affinity_id, build_id
            )
        except ImpossibleAction as exc:
            return Description(title="Action impossible", items=[Part(text=str(exc))])

        self._kernel.spawn_point_lib.create_from_build(affinity_id, build_id)

        return Description(
            title="Point d'apparition créé !",
            items=[
                Part(
                    text=(
                        "Désormais, les nouveaux personnages pourront choisir "
                        "ce lieu pour apparaitre dans votre monde"
                    )
                )
            ],
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.post(
                    "/spawn/{character_id}/from-build/{build_id}",
                    self.management_from_build,
                ),
                web.post(
                    "/spawn/{character_id}/from-build/{build_id}/create/{affinity_id}",
                    self.create_from_build,
                ),
            ]
        )
