# coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from collections import namedtuple
from hapic import HapicData
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.exception import NoZoneMapError
from rolling.kernel import Kernel
from rolling.map.type.base import MapTileType
from rolling.model.build import ZoneBuildModel
from rolling.model.build import ZoneBuildModelContainer
from rolling.model.character import CharacterModel
from rolling.model.meta import TransportType
from rolling.model.resource import OnGroundResourceModel
from rolling.model.stuff import StuffModel
from rolling.model.zone import GetZoneCharacterPathModel
from rolling.model.zone import GetZoneMessageQueryModel
from rolling.model.zone import GetZonePathModel
from rolling.model.zone import GetZoneQueryModel
from rolling.model.zone import ZoneMapModel
from rolling.model.zone import ZoneTileTypeModel
from rolling.server.controller.base import BaseController
from rolling.server.controller.url import DESCRIBE_LOOK_AT_CHARACTER_URL
from rolling.server.extension import hapic
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.server.lib.zone import ZoneLib
from rolling.server.processor import RollingSerpycoProcessor
from rolling.availability import Availability


class ZoneController(BaseController):
    def __init__(
        self,
        kernel: Kernel,
        character_lib: typing.Optional[CharacterLib] = None,
        stuff_lib: typing.Optional[StuffLib] = None,
    ) -> None:
        self._kernel = kernel
        self._tile_lib = ZoneLib(self._kernel)
        self._character_lib = character_lib or CharacterLib(self._kernel)
        self._stuff_lib = stuff_lib or StuffLib(self._kernel)

    @hapic.with_api_doc()
    @hapic.output_body(ZoneTileTypeModel, processor=RollingSerpycoProcessor(many=True))
    async def get_tiles(self, request: Request) -> typing.List[ZoneTileTypeModel]:
        return self._tile_lib.get_all_tiles()

    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZonePathModel)
    @hapic.output_body(ZoneMapModel)
    async def get_zone(self, request: Request, hapic_data: HapicData) -> ZoneMapModel:
        return self._tile_lib.get_zone(
            row_i=hapic_data.path.row_i, col_i=hapic_data.path.col_i
        )

    async def events(self, request: Request):
        # TODO BS 2019-01-23: Establish zone websocket must require character in zone
        return await self._kernel.server_zone_events_manager.get_new_socket(
            request,
            row_i=int(request.match_info["row_i"]),
            col_i=int(request.match_info["col_i"]),
            character_id=request.query["character_id"],
            reader_token=request.query.get("reader_token"),
            token=request.query.get("token"),
        )

    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZonePathModel)
    @hapic.output_body(CharacterModel, processor=RollingSerpycoProcessor(many=True))
    async def get_characters(
        self, request: Request, hapic_data: HapicData
    ) -> typing.List[CharacterModel]:
        return self._character_lib.get_zone_characters(
            row_i=request.match_info["row_i"], col_i=request.match_info["col_i"]
        )

    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZonePathModel)
    @hapic.output_body(StuffModel, processor=RollingSerpycoProcessor(many=True))
    async def get_stuff(
        self, request: Request, hapic_data: HapicData
    ) -> typing.List[StuffModel]:
        return self._stuff_lib.get_zone_stuffs(
            world_row_i=request.match_info["row_i"],
            world_col_i=request.match_info["col_i"],
        )

    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZonePathModel)
    @hapic.output_body(
        OnGroundResourceModel, processor=RollingSerpycoProcessor(many=True)
    )
    async def get_resources(
        self, request: Request, hapic_data: HapicData
    ) -> typing.List[OnGroundResourceModel]:
        return [
            OnGroundResourceModel(
                id=c.id,
                quantity=c.quantity,
                zone_row_i=c.ground_row_i,
                zone_col_i=c.ground_col_i,
            )
            for c in self._kernel.resource_lib.get_ground_resource(
                world_row_i=hapic_data.path.row_i, world_col_i=hapic_data.path.col_i
            )
        ]

    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZonePathModel)
    @hapic.input_query(GetZoneQueryModel)
    @hapic.output_body(ZoneBuildModel, processor=RollingSerpycoProcessor(many=True))
    async def get_builds(
        self, request: Request, hapic_data: HapicData
    ) -> typing.List[ZoneBuildModelContainer]:
        build_docs = self._kernel.build_lib.get_zone_build(
            world_row_i=hapic_data.path.row_i, world_col_i=hapic_data.path.col_i
        )
        zone_builds: typing.List[typing.Optional[ZoneBuildModelContainer]] = [
            None
        ] * len(
            build_docs
        )  # performances (possible lot of builds)
        for i, build_doc in enumerate(build_docs):
            build_description = self._kernel.game.config.builds[build_doc.build_id]
            build_container = ZoneBuildModelContainer(
                doc=build_doc, desc=build_description
            )
            if build_description.is_door:
                can_walk = False
                if not hapic_data.query.disable_door_compute:
                    can_walk = not self._kernel.door_lib.is_access_locked_for(
                        build_id=build_doc.id,
                        character_id=request["account_character_id"],
                    )
                build_container.traversable = {TransportType.WALKING: can_walk}

            # FIXME BS NOW farm
            if build_description.id == "PLOUGHED_LAND":
                growing_state_classes = (
                    self._kernel.farming_lib.get_growing_state_classes(build=build_doc)
                )
                build_container.classes = (
                    build_description.classes
                    + [build_doc.build_id]
                    + growing_state_classes
                )

            zone_builds[i] = build_container

        return zone_builds

    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZoneCharacterPathModel)
    @hapic.output_body(Description)
    async def describe(self, request: Request, hapic_data: HapicData) -> Description:
        world_rows = self._kernel.world_map_source.geography.rows
        tile_type: MapTileType = world_rows[hapic_data.path.row_i][
            hapic_data.path.col_i
        ]
        zone_properties = self._kernel.game.world_manager.get_zone_properties(tile_type)
        character = self._kernel.character_lib.get(hapic_data.path.character_id)
        characters = self._kernel.character_lib.get_zone_characters(
            hapic_data.path.row_i, hapic_data.path.col_i
        )
        characters_parts: typing.List[Part] = []
        for character in characters:
            if character.id != hapic_data.path.character_id:
                characters_parts.append(
                    Part(
                        label=character.name,
                        is_link=True,
                        form_action=DESCRIBE_LOOK_AT_CHARACTER_URL.format(
                            character_id=hapic_data.path.character_id,
                            with_character_id=character.id,
                        ),
                    )
                )

        if characters_parts:
            characters_parts.insert(
                0, Part(text=f"Dans cette zone se trouvent les personnages suivants:")
            )
        else:
            characters_parts = [Part("Vous êtes seul dans la zone.")]

        affinities_parts = []
        for affinity_relation in self._kernel.affinity_lib.get_accepted_affinities(
            character.id
        ):
            affinity = self._kernel.affinity_lib.get_affinity(
                affinity_relation.affinity_id
            )
            here_count = self._kernel.affinity_lib.count_members(
                affinity.id,
                fighter=None,
                world_row_i=hapic_data.path.row_i,
                world_col_i=hapic_data.path.col_i,
                exclude_character_ids=[character.id],
            )
            if here_count:
                fighter_here_count = self._kernel.affinity_lib.count_members(
                    affinity.id,
                    fighter=True,
                    world_row_i=hapic_data.path.row_i,
                    world_col_i=hapic_data.path.col_i,
                    exclude_character_ids=[character.id],
                )
                affinities_parts.append(
                    Part(
                        text=f"Sur cette zone, il y a actuellement avec vous {here_count} "
                        f"membre(s) de {affinity.name} (dont {fighter_here_count} "
                        f"combattant(s))"
                    )
                )

        character_affinity_ids = [
            r.affinity_id
            for r in self._kernel.affinity_lib.get_accepted_affinities(character.id)
        ]
        for relation in self._kernel.affinity_lib.get_zone_relations(
            row_i=character.world_row_i,
            col_i=character.world_col_i,
            accepted=True,
            affinity_ids=character_affinity_ids,
            exclude_character_ids=[character.id],
        ):
            affinity = self._kernel.affinity_lib.get_affinity(relation.affinity_id)
            affinities_parts.append(
                Part(
                    is_link=True,
                    label=f"Fiche de {affinity.name}",
                    form_action=f"/affinity/{character.id}/see/{affinity.id}",
                )
            )

        if affinities_parts:
            affinities_parts.insert(0, Part(""))

        availability = Availability.new(self._kernel, character)
        availability_parts = [Part("")]

        if protectorate_affinity := availability.under_protectorate():
            availability_parts.append(
                Part(
                    f"Cette zone est soumise au protectorat de {protectorate_affinity.name} "
                    "Les accès aux biens de cette zone sont les suivants :"
                ),
            )
        else:
            availability_parts.append(
                Part(
                    "Cette zone n'est pas soumise à un protectorat. "
                    "Les accès aux biens de cette zone sont les suivants :"
                ),
            )

        if availability.can_pickup_from_ground():
            availability_parts.append(Part("  ✅ Prendre le matériel déposé au sol"))
        else:
            availability_parts.append(
                Part("  ❌ Vous ne pouvez pas prendre matériel déposé au sol")
            )

        if availability.can_extract():
            availability_parts.append(Part("  ✅ Exploiter les ressources naturelles"))
        else:
            availability_parts.append(
                Part("  ❌ Vous ne pouvez pas exploiter les ressources naturelles")
            )

        if availability.can_use_builds():
            availability_parts.append(Part("  ✅ Utiliser les bâtiments"))
        else:
            availability_parts.append(
                Part("  ❌ Vous ne pouvez pas utiliser les bâtiments")
            )

        availability_parts.append(Part(""))

        return Description(
            title=tile_type.get_name(),
            illustration_name=zone_properties.illustration,
            items=[
                Part(text=f"Vous vous trouvez sur {tile_type.get_name()}."),
                Part(text=zone_properties.description),
            ]
            + affinities_parts
            + availability_parts
            + characters_parts,
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZonePathModel)
    @hapic.input_query(GetZoneMessageQueryModel)
    @hapic.output_body(Description)
    async def messages(self, request: Request, hapic_data: HapicData) -> Description:
        assert request["account_character_id"] == hapic_data.query.character_id
        messages = self._kernel.message_lib.get_character_zone_messages(
            character_id=hapic_data.query.character_id
        )
        self._kernel.message_lib.mark_character_zone_messages_as_read(
            character_id=hapic_data.query.character_id
        )

        message_parts: typing.List[Part] = []
        for message in messages:
            if message.is_outzone_message:
                message_parts.append(
                    Part(text=message.text or "Vous avez quitté la zone")
                )
            else:
                message_parts.append(
                    Part(text=f"{message.author_name}: {message.text}")
                )

        return Description(
            title="Messagerie de zone",
            items=[
                Part(
                    text=f"Cette messagerie regroupe les conversations que votre personnage à tenu "
                    f"avec tous les personnages se trouvant dans la même zone que lui. "
                    f"Lorsque vous vous exprimez ici, tous les personnages se trouvant sur la "
                    f"même zone écoutent."
                ),
                Part(
                    is_form=True,
                    form_action=f"/zones/{hapic_data.path.row_i}/{hapic_data.path.col_i}"
                    f"/messages/add?character_id={hapic_data.query.character_id}",
                    items=[
                        Part(
                            label=f"Parler aux personnes presentes ?",
                            type_=Type.STRING,
                            name="message",
                        )
                    ],
                ),
                Part(label=""),
            ]
            + message_parts,
            can_be_back_url=True,
        )

    # FIXME : delete this view by conversation reforming
    @hapic.with_api_doc()
    @hapic.handle_exception(NoZoneMapError, http_code=404)
    @hapic.input_path(GetZonePathModel)
    @hapic.input_query(GetZoneMessageQueryModel)
    @hapic.output_body(Description)
    async def add_message(self, request: Request, hapic_data: HapicData) -> Description:
        post_content = await request.json()
        await self._kernel.message_lib.add_zone_message(
            hapic_data.query.character_id,
            message=post_content["message"],
            zone_row_i=hapic_data.path.row_i,
            zone_col_i=hapic_data.path.col_i,
        )

        return Description(
            redirect=(
                f"/zones/{hapic_data.path.row_i}/{hapic_data.path.col_i}"
                f"/messages?character_id={hapic_data.query.character_id}"
            )
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.get("/zones/tiles", self.get_tiles),
                web.get("/zones/{row_i}/{col_i}", self.get_zone),
                web.get("/zones/{row_i}/{col_i}/events", self.events),
                web.get("/ws/zones/{row_i}/{col_i}/events", self.events),
                web.get("/zones/{row_i}/{col_i}/characters", self.get_characters),
                web.get("/zones/{row_i}/{col_i}/stuff", self.get_stuff),
                web.get("/zones/{row_i}/{col_i}/resources", self.get_resources),
                web.get("/zones/{row_i}/{col_i}/builds", self.get_builds),
                web.post(
                    "/zones/{row_i}/{col_i}/describe/{character_id}", self.describe
                ),
                web.post("/zones/{row_i}/{col_i}/messages", self.messages),
                web.post("/zones/{row_i}/{col_i}/messages/add", self.add_message),
            ]
        )
