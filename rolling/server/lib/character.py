# coding: utf-8
import typing
import uuid

from rolling.exception import ImpossibleAction
from rolling.model.ability import HaveAbility
from rolling.model.character import CharacterEventModel
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel
from rolling.model.meta import FromType
from rolling.model.meta import RiskType
from rolling.model.stuff import CharacterInventoryModel
from rolling.model.stuff import StuffModel
from rolling.model.zone import MoveZoneInfos
from rolling.server.action import ActionFactory
from rolling.server.controller.url import DESCRIBE_BUILD
from rolling.server.controller.url import DESCRIBE_LOOT_AT_STUFF_URL
from rolling.server.controller.url import TAKE_STUFF_URL
from rolling.server.document.character import CharacterDocument
from rolling.server.document.event import EventDocument
from rolling.server.lib.stuff import StuffLib
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType
from rolling.util import filter_action_links
from rolling.util import get_on_and_around_coordinates

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class CharacterLib:
    def __init__(self, kernel: "Kernel", stuff_lib: typing.Optional[StuffLib] = None) -> None:
        self._kernel = kernel
        self._stuff_lib: StuffLib = stuff_lib or StuffLib(kernel)
        self._action_factory = ActionFactory(kernel)

    def create(self, create_character_model: CreateCharacterModel) -> str:
        character = CharacterDocument()
        character.id = uuid.uuid4().hex
        character.name = create_character_model.name
        character.background_story = create_character_model.background_story
        character.hunting_and_collecting_comp = create_character_model.hunting_and_collecting_comp
        character.find_water_comp = create_character_model.find_water_comp
        character.max_life_comp = create_character_model.max_life_comp
        character.life_points = character.max_life_comp
        character.action_points = self._kernel.game.config.action_points_per_turn

        # Place on zone
        world_row_i, world_col_i = self._kernel.world_map_source.meta.spawn.get_spawn_coordinates(
            self._kernel.world_map_source
        )
        start_zone_source = self._kernel.tile_maps_by_position[world_row_i, world_col_i].source
        zone_row_i, zone_col_i = start_zone_source.get_start_zone_coordinates(
            world_row_i, world_col_i
        )

        character.world_row_i = world_row_i
        character.world_col_i = world_col_i
        character.zone_row_i = zone_row_i
        character.zone_col_i = zone_col_i

        self._kernel.server_db_session.add(character)
        self._kernel.server_db_session.commit()

        for message in self._kernel.game.config.create_character_messages:
            self.add_event(character.id, message)

        return character.id

    def get_document(self, id_: str) -> CharacterDocument:
        return (
            self._kernel.server_db_session.query(CharacterDocument)
            .filter(CharacterDocument.id == id_)
            .one()
        )

    def get_document_by_name(self, name: str) -> CharacterDocument:
        return (
            self._kernel.server_db_session.query(CharacterDocument)
            .filter(CharacterDocument.name == name)
            .one()
        )

    def document_to_model(self, character_document: CharacterDocument) -> CharacterModel:
        return CharacterModel(
            id=character_document.id,
            name=character_document.name,
            world_col_i=character_document.world_col_i,
            world_row_i=character_document.world_row_i,
            zone_col_i=character_document.zone_col_i,
            zone_row_i=character_document.zone_row_i,
            background_story=character_document.background_story,
            life_points=float(character_document.life_points),
            max_life_comp=float(character_document.max_life_comp),
            hunting_and_collecting_comp=float(character_document.hunting_and_collecting_comp),
            find_water_comp=float(character_document.find_water_comp),
            feel_thirsty=character_document.feel_thirsty,
            feel_hungry=character_document.feel_hungry,
            dehydrated=character_document.dehydrated,
            starved=character_document.starved,
            action_points=float(character_document.action_points),
            bags=[
                self._stuff_lib.stuff_model_from_doc(bag_doc)
                for bag_doc in character_document.used_as_bag
            ],
        )

    def get(self, id_: str) -> CharacterModel:
        character_document = self.get_document(id_)
        return self.document_to_model(character_document)

    def get_by_name(self, name: str) -> CharacterModel:
        character_document = self.get_document_by_name(name)
        return self.document_to_model(character_document)

    def move_on_zone(self, character: CharacterModel, to_row_i: int, to_col_i: int) -> None:
        character_document = self.get_document(character.id)
        character_document.zone_row_i = to_row_i
        character_document.zone_col_i = to_col_i
        self._kernel.server_db_session.add(character_document)
        self._kernel.server_db_session.commit()

    def get_zone_players(self, row_i: int, col_i: int) -> typing.List[CharacterModel]:
        character_documents = (
            self._kernel.server_db_session.query(CharacterDocument)
            .filter(CharacterDocument.world_row_i == row_i)
            .filter(CharacterDocument.world_col_i == col_i)
            .all()
        )

        return [
            self.document_to_model(character_document) for character_document in character_documents
        ]

    def move(self, character: CharacterModel, to_world_row: int, to_world_col: int) -> None:
        # TODO BS 2019-06-04: Check if move is possible
        # TODO BS 2019-06-04: Compute how many action point and consume
        character_document = self.get_document(character.id)
        character_document.world_row_i = to_world_row
        character_document.world_col_i = to_world_col
        self.update(character_document)

    def update(self, character_document: CharacterDocument, commit: bool = True) -> None:
        self._kernel.server_db_session.add(character_document)
        if commit:
            self._kernel.server_db_session.commit()

    def get_all_character_count(self) -> int:
        return self._kernel.server_db_session.query(CharacterDocument.id).count()

    def get_all_character_ids(self) -> typing.Iterable[str]:
        return (row[0] for row in self._kernel.server_db_session.query(CharacterDocument.id).all())

    def get_inventory(self, character_id: str) -> CharacterInventoryModel:
        carried_stuff = self._stuff_lib.get_carried_by(character_id)
        carried_resources = self._kernel.resource_lib.get_carried_by(character_id)

        total_weight = sum([stuff.weight for stuff in carried_stuff if stuff.weight])
        total_weight += sum([r.weight for r in carried_resources if r.weight])

        total_clutter = sum([stuff.clutter for stuff in carried_stuff if stuff.clutter])
        total_clutter += sum([r.clutter for r in carried_resources if r.clutter])

        return CharacterInventoryModel(
            stuff=carried_stuff,
            resource=carried_resources,
            weight=total_weight,
            clutter=total_clutter,
        )

    def get_on_place_actions(self, character_id: str) -> typing.List[CharacterActionLink]:
        character = self.get(character_id)
        around_character = get_on_and_around_coordinates(
            x=character.zone_row_i, y=character.zone_col_i
        )
        character_actions_: typing.List[CharacterActionLink] = []

        # Actions with near items
        on_same_position_items = self._stuff_lib.get_zone_stuffs(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
        )
        for item in on_same_position_items:
            character_actions_.append(
                CharacterActionLink(
                    name=f"Jeter un coup d'oeil sur {item.name}",
                    link=DESCRIBE_LOOT_AT_STUFF_URL.format(
                        character_id=character_id, stuff_id=item.id
                    ),
                )
            )

        # Actions with near items
        for around_row_i, around_col_i in around_character:
            on_same_position_builds = self._kernel.build_lib.get_zone_build(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
            )
            for build in on_same_position_builds:
                build_description = self._kernel.game.config.builds[build.build_id]
                character_actions_.append(
                    CharacterActionLink(
                        name=f"Jeter un coup d'oeil sur {build_description.name}",
                        link=DESCRIBE_BUILD.format(character_id=character_id, build_id=build.id),
                    )
                )

        # Actions with available character actions
        for action in self._action_factory.get_all_character_actions():
            character_actions_.extend(action.get_character_actions(character))

        return filter_action_links(character_actions_)

    def get_build_actions(self, character_id: str) -> typing.List[CharacterActionLink]:
        character = self.get(character_id)
        character_actions_: typing.List[CharacterActionLink] = []

        for action in self._action_factory.get_all_build_actions():
            character_actions_.extend(action.get_character_actions(character))

        return filter_action_links(character_actions_)

    def get_on_stuff_actions(
        self, character_id: str, stuff_id: int
    ) -> typing.List[CharacterActionLink]:
        stuff = self._stuff_lib.get_stuff(stuff_id)
        character = self.get(character_id)
        character_actions: typing.List[CharacterActionLink] = []

        if stuff.carried_by is None:
            character_actions.append(
                CharacterActionLink(
                    name=f"Take {stuff.get_name_and_light_description()}",
                    link=TAKE_STUFF_URL.format(character_id=character_id, stuff_id=stuff.id),
                )
            )
        elif stuff.carried_by == character_id:
            character_actions.extend(self._stuff_lib.get_carrying_actions(character, stuff))

        return filter_action_links(character_actions)

    def get_on_resource_actions(
        self, character_id: str, resource_id: str
    ) -> typing.List[CharacterActionLink]:
        character = self.get(character_id)
        character_actions = self._kernel.resource_lib.get_carrying_actions(character, resource_id)
        return filter_action_links(character_actions)

    def take_stuff(self, character_id: str, stuff_id: int) -> None:
        self._stuff_lib.set_carried_by(stuff_id=stuff_id, character_id=character_id)

    def drink_material(self, character_id: str, resource_id: str) -> str:
        character_doc = self.get_document(character_id)

        if not character_doc.feel_thirsty:
            return "Vous n'avez pas soif"

        if resource_id == self._kernel.game.config.fresh_water_resource_id:
            character_doc.dehydrated = False
            character_doc.feel_thirsty = False
            self._kernel.server_db_session.add(character_doc)
            self._kernel.server_db_session.commit()
            return "Vous n'avez plus soif"

        # TODO BS 2019-09-02: drink wine etc ?
        return "Vous ne pouvez pas boire ça"

    def drink_stuff(self, character_id: str, stuff_id: int, commit: bool = True) -> None:
        character_doc = self.get_document(character_id)
        stuff_doc = self._stuff_lib.get_stuff_doc(stuff_id)
        stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
            stuff_doc.stuff_id
        )

        # TODO BS 2019-07-09: manage case where not 100% filled
        if float(stuff_doc.filled_at) == 100.0:
            stuff_doc.empty(stuff_properties)
            self._kernel.server_db_session.add(stuff_doc)

            character_doc.feel_thirsty = False
            character_doc.dehydrated = False

            if commit:
                self._kernel.server_db_session.commit()

        raise ImpossibleAction("pas encore codé")

    def get_last_events(
        self, character_id: str, count: int
    ) -> typing.Iterator[CharacterEventModel]:
        for event_doc in (
            self._kernel.server_db_session.query(EventDocument)
            .filter(EventDocument.character_id == character_id)
            .order_by(EventDocument.datetime.desc())
            .limit(count)
        ):
            yield CharacterEventModel(datetime=event_doc.datetime, text=event_doc.text)

    def add_event(self, character_id: str, text: str) -> None:
        self._kernel.server_db_session.add(EventDocument(character_id=character_id, text=text))
        self._kernel.server_db_session.commit()

    def get_used_bags(self, character_id: str) -> typing.List[StuffModel]:
        return self._stuff_lib.get_carried_and_used_bags(character_id)

    def reduce_action_points(self, character_id: str, cost: float, commit: bool = True) -> None:
        character_doc = self.get_document(character_id)
        character_doc.action_points = float(character_doc.action_points) - cost
        self._kernel.server_db_session.add(character_doc)

        if commit:
            self._kernel.server_db_session.commit()

    def get_move_to_zone_infos(
        self, character_id: str, world_row_i: int, world_col_i: int
    ) -> MoveZoneInfos:
        zone_type = self._kernel.world_map_source.geography.rows[world_row_i][world_col_i]
        move_cost = self._kernel.game.world_manager.get_zone_properties(zone_type).move_cost
        character = self.get(character_id)

        return MoveZoneInfos(can_move=character.action_points >= move_cost, cost=move_cost)

    def have_from_of_abilities(
        self, character: CharacterModel, abilities: typing.List[str]
    ) -> typing.List[HaveAbility]:
        haves: typing.List[HaveAbility] = []

        if character.have_one_of_abilities(abilities):
            haves.append(HaveAbility(from_=FromType.CHARACTER, risk=RiskType.NONE))

        for stuff in self._kernel.stuff_lib.get_carried_by(character.id):
            stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                stuff.stuff_id
            )
            if stuff_properties.have_one_of_abilities(abilities):
                haves.append(HaveAbility(from_=FromType.STUFF, risk=RiskType.NONE))

        return haves
