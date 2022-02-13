# coding: utf-8
import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithBuildAction
from rolling.action.base import get_with_build_action_url
from rolling.exception import ImpossibleAction
from rolling.model.build import ZoneBuildModelContainer
from rolling.model.event import NewBuildData, WebSocketEvent, ZoneEventType
from rolling.rolling_types import ActionType
from rolling.server.document.build import BuildDocument
from rolling.server.link import CharacterActionLink
from rolling.util import EmptyModel

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


async def send_new_build(
    kernel: "Kernel", character: "CharacterModel", build: BuildDocument
) -> None:
    build_description = kernel.game.config.builds[build.build_id]
    await kernel.server_zone_events_manager.send_to_sockets(
        WebSocketEvent(
            type=ZoneEventType.NEW_BUILD,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            data=NewBuildData(
                build=ZoneBuildModelContainer(doc=build, desc=build_description)
            ),
        ),
        world_row_i=character.world_row_i,
        world_col_i=character.world_col_i,
    )


class PowerOnBuildAction(WithBuildAction):
    input_model = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", build_id: int) -> None:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        if not build_description.power_on_require_resources:
            raise ImpossibleAction("Ne peut pas être démarré")

    async def check_request_is_possible(
        self, character: "CharacterModel", build_id: int, input_: EmptyModel
    ) -> None:
        self.check_is_possible(character, build_id)
        pass

    def get_character_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        return [
            CharacterActionLink(
                name="Démarrer",
                link=get_with_build_action_url(
                    character_id=character.id,
                    build_id=build_id,
                    action_type=ActionType.POWER_ON_BUILD,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                classes1=["ON"],
                classes2=build_description.classes,
                direct_action=True,
            )
        ]

    def get_quick_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        return [
            link.clone_for_quick_action()
            for link in self.get_character_actions(character, build_id=build_id)
        ]

    async def perform(
        self, character: "CharacterModel", build_id: int, input_: EmptyModel
    ) -> Description:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        missing_parts: typing.List[Part] = []
        parts: typing.List[Part] = []

        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        if build_doc.is_on:
            raise ImpossibleAction("Batiment en fonctionnement")
        if build_doc.under_construction:
            raise ImpossibleAction("Batiment en construction")
        if build_doc.is_on:
            raise ImpossibleAction("Batiment déjà démarré")

        for required in build_description.power_on_require_resources:
            resource_description = self._kernel.game.config.resources[
                required.resource_id
            ]
            if not self._kernel.resource_lib.have_resource(
                resource_id=required.resource_id,
                build_id=build_id,
                quantity=required.quantity,
            ):
                unit_str = self._kernel.translation.get(
                    resource_description.unit, short=True
                )
                raise ImpossibleAction(f"{resource_description.name}{unit_str} requis")

        for required in build_description.power_on_require_resources:
            self._kernel.resource_lib.reduce_stored_in(
                resource_id=required.resource_id,
                quantity=required.quantity,
                build_id=build_id,
                commit=False,
            )
        build_doc.is_on = True
        self._kernel.server_db_session.commit()
        parts.append(Part(text=f"{build_description.name} démarré avec succès"))
        await send_new_build(self._kernel, character, build_doc)

        quick_text = "Démarré" if not missing_parts else "Pas assez de stock"
        return Description(
            title=f"Démarrer {build_description.name}",
            items=parts + missing_parts,
            footer_with_build_id=build_id,
            quick_action_response=quick_text,
        )


class PowerOffBuildAction(WithBuildAction):
    input_model = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", build_id: int) -> None:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        if not build_description.power_on_require_resources:
            raise ImpossibleAction("Ce batiment ne se démarre pas")
        if not build_doc.is_on:
            raise ImpossibleAction("Ce batiment n'est pas en fonctionnement")

    async def check_request_is_possible(
        self, character: "CharacterModel", build_id: int, input_: EmptyModel
    ) -> None:
        self.check_is_possible(character, build_id)
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        if not build_doc.is_on:
            raise ImpossibleAction("Ce batiment n'est pas démarré")

    def get_character_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        return [
            CharacterActionLink(
                name="Arrêter",
                link=get_with_build_action_url(
                    character_id=character.id,
                    build_id=build_id,
                    action_type=ActionType.POWER_OFF_BUILD,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                classes1=["OFF"],
                classes2=build_description.classes,
                direct_action=True,
            )
        ]

    def get_quick_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        return [
            link.clone_for_quick_action()
            for link in self.get_character_actions(character, build_id=build_id)
        ]

    async def perform(
        self, character: "CharacterModel", build_id: int, input_: EmptyModel
    ) -> Description:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]

        build_doc.is_on = False
        self._kernel.server_db_session.commit()
        await send_new_build(self._kernel, character, build_doc)

        return Description(
            title=f"Arrêter {build_description.name}",
            items=[Part(text="Arrêté avec succès")],
            footer_with_build_id=build_id,
            quick_action_response="Arrêté",
        )
