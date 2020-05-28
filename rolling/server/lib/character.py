# coding: utf-8
import os
import typing
import uuid

import sqlalchemy
from sqlalchemy import and_
from sqlalchemy.orm import Query
from sqlalchemy.orm.exc import NoResultFound

from rolling.exception import ImpossibleAction
from rolling.model.ability import AbilityDescription
from rolling.model.ability import HaveAbility
from rolling.model.character import FIGHT_AP_CONSUME
from rolling.model.character import MINIMUM_BEFORE_EXHAUSTED
from rolling.model.character import CharacterEventModel
from rolling.model.character import CharacterModel
from rolling.model.character import CreateCharacterModel
from rolling.model.event import StoryPage
from rolling.model.meta import FromType
from rolling.model.meta import RiskType
from rolling.model.stuff import CharacterInventoryModel
from rolling.model.stuff import StuffModel
from rolling.model.zone import MoveZoneInfos
from rolling.server.action import ActionFactory
from rolling.server.controller.url import DESCRIBE_BUILD
from rolling.server.controller.url import DESCRIBE_LOOK_AT_CHARACTER_URL
from rolling.server.controller.url import DESCRIBE_LOOK_AT_RESOURCE_URL
from rolling.server.controller.url import DESCRIBE_LOOK_AT_STUFF_URL
from rolling.server.controller.url import TAKE_STUFF_URL
from rolling.server.document.affinity import CHIEF_STATUS
from rolling.server.document.affinity import AffinityDirectionType
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityRelationDocument
from rolling.server.document.base import ImageDocument
from rolling.server.document.business import OfferDocument
from rolling.server.document.character import CharacterDocument
from rolling.server.document.event import EventDocument
from rolling.server.document.event import StoryPageDocument
from rolling.server.document.message import MessageDocument
from rolling.server.lib.stuff import StuffLib
from rolling.server.link import CharacterActionLink
from rolling.server.util import register_image
from rolling.types import ActionType
from rolling.util import filter_action_links
from rolling.util import get_coming_from
from rolling.util import get_on_and_around_coordinates
from rolling.util import get_opposite_zone_place

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class CharacterLib:
    def __init__(self, kernel: "Kernel", stuff_lib: typing.Optional[StuffLib] = None) -> None:
        self._kernel = kernel
        self._stuff_lib: StuffLib = stuff_lib or StuffLib(kernel)
        self._action_factory = ActionFactory(kernel)

    @property
    def alive_query(self) -> Query:
        return self._kernel.server_db_session.query(CharacterDocument).filter(
            CharacterDocument.alive == True
        )

    @property
    def dead_query(self) -> Query:
        return self._kernel.server_db_session.query(CharacterDocument).filter(
            CharacterDocument.alive == False
        )

    @property
    def dont_care_alive_query(self) -> Query:
        return self._kernel.server_db_session.query(CharacterDocument)

    def create(self, create_character_model: CreateCharacterModel) -> str:
        character = CharacterDocument()
        character.id = uuid.uuid4().hex
        character.name = create_character_model.name
        # character.background_story = create_character_model.background_story
        # character.hunting_and_collecting_comp = create_character_model.hunting_and_collecting_comp
        # character.find_water_comp = create_character_model.find_water_comp
        character.max_life_comp = float(create_character_model.max_life_comp)
        character.life_points = float(character.max_life_comp)
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

        image_id = None
        if self._kernel.game.config.create_character_event_story_image:
            image_id = register_image(
                self._kernel,
                os.path.join(
                    self._kernel.game.config.folder_path,
                    "media",
                    self._kernel.game.config.create_character_event_story_image,
                ),
            )

        event = self.add_event(character.id, self._kernel.game.config.create_character_event_title)
        first_story_page = StoryPageDocument(
            event_id=event.id,
            text=self._kernel.game.config.create_character_event_story_text,
            image_id=image_id,
        )
        self.add_story_pages([first_story_page])

        return character.id

    def get_document(self, id_: str, dead: typing.Optional[bool] = False) -> CharacterDocument:
        if dead is None:
            query = self.dont_care_alive_query
        elif dead:
            query = self.dead_query
        else:
            query = self.alive_query
        return query.filter(CharacterDocument.id == id_).one()

    def get_document_by_name(self, name: str) -> CharacterDocument:
        return self.alive_query.filter(CharacterDocument.name == name).one()

    def document_to_model(self, character_document: CharacterDocument) -> CharacterModel:
        weapon = None
        weapon_doc = character_document.used_as_primary_weapon
        if weapon_doc:
            weapon = self._kernel.stuff_lib.stuff_model_from_doc(weapon_doc)

        shield = None
        shield_doc = character_document.used_as_shield
        if shield_doc:
            shield = self._kernel.stuff_lib.stuff_model_from_doc(shield_doc)

        armor = None
        armor_doc = character_document.used_as_armor
        if armor_doc:
            armor = self._kernel.stuff_lib.stuff_model_from_doc(armor_doc)

        return CharacterModel(
            id=character_document.id,
            name=character_document.name,
            attack_allowed_loss_rate=character_document.attack_allowed_loss_rate,
            defend_allowed_loss_rate=character_document.defend_allowed_loss_rate,
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
            tiredness=character_document.tiredness,
            action_points=float(character_document.action_points),
            bags=[
                self._stuff_lib.stuff_model_from_doc(bag_doc)
                for bag_doc in character_document.used_as_bag
            ],
            weapon=weapon,
            shield=shield,
            armor=armor,
        )

    def get_multiple(self, character_ids: typing.List[str]) -> typing.List[CharacterModel]:
        return [
            self.document_to_model(doc)
            for doc in self.alive_query.filter(CharacterDocument.id.in_(character_ids)).all()
        ]

    def get(
        self,
        id_: str,
        compute_unread_event: bool = False,
        compute_unread_zone_message: bool = False,
        compute_unread_conversation: bool = False,
        compute_unvote_affinity_relation: bool = False,
        compute_unread_transactions: bool = False,
    ) -> CharacterModel:
        character_document = self.get_document(id_)
        model = self.document_to_model(character_document)

        # TODO BS: Move these compute unread/unvote in respective libs
        if (
            compute_unread_event
            and self._kernel.server_db_session.query(EventDocument.id)
            .filter(and_(EventDocument.character_id == id_, EventDocument.read == False))
            .count()
        ):
            model.unread_event = True

        if (
            compute_unread_zone_message
            and self._kernel.server_db_session.query(MessageDocument.id)
            .filter(
                MessageDocument.character_id == id_,
                MessageDocument.zone_row_i != None,
                MessageDocument.zone_col_i != None,
                MessageDocument.read == False,
            )
            .count()
        ):
            model.unread_zone_message = True

        if (
            compute_unread_conversation
            and self._kernel.server_db_session.query(MessageDocument.id)
            .filter(
                MessageDocument.character_id == id_,
                MessageDocument.zone == False,
                MessageDocument.read == False,
            )
            .count()
        ):
            model.unread_conversation = True

        if compute_unvote_affinity_relation:
            character_chief_affinity_ids = [
                r[0]
                for r in self._kernel.server_db_session.query(AffinityRelationDocument.affinity_id)
                .filter(
                    AffinityRelationDocument.character_id == character_document.id,
                    AffinityRelationDocument.accepted == True,
                    AffinityRelationDocument.status_id == CHIEF_STATUS[0],
                )
                .all()
            ]
            # TODO BS: implement other direction types
            character_chief_affinity_ids = [
                a[0]
                for a in self._kernel.server_db_session.query(AffinityDocument.id)
                .filter(
                    AffinityDocument.id.in_(character_chief_affinity_ids),
                    AffinityDocument.direction_type.in_([AffinityDirectionType.ONE_DIRECTOR.value]),
                )
                .all()
            ]
            if (
                self._kernel.server_db_session.query(AffinityRelationDocument)
                .filter(
                    AffinityRelationDocument.affinity_id.in_(character_chief_affinity_ids),
                    AffinityRelationDocument.accepted == False,
                    AffinityRelationDocument.request == True,
                )
                .count()
            ):
                model.unvote_affinity_relation = True

        if compute_unread_transactions:
            if (
                self._kernel.business_lib.get_incoming_transactions_query(id_)
                .filter(OfferDocument.read == False)
                .count()
            ):
                model.unread_transactions = True

        return model

    def get_by_name(self, name: str) -> CharacterModel:
        character_document = self.get_document_by_name(name)
        return self.document_to_model(character_document)

    def move_on_zone(
        self, character: CharacterModel, to_row_i: int, to_col_i: int
    ) -> CharacterDocument:
        character_document = self.get_document(character.id)
        character_document.zone_row_i = to_row_i
        character_document.zone_col_i = to_col_i

        self._kernel.server_db_session.add(character_document)
        self._kernel.server_db_session.commit()

        return character_document

    # TODO BS: rename into get_zone_characters
    def get_zone_players(
        self,
        row_i: int,
        col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
        exclude_ids: typing.Optional[typing.List[str]] = None,
    ) -> typing.List[CharacterModel]:
        exclude_ids = exclude_ids or []
        filters = [CharacterDocument.world_row_i == row_i, CharacterDocument.world_col_i == col_i]

        if exclude_ids:
            filters.extend([CharacterDocument.id.notin_(exclude_ids)])

        if zone_row_i is not None and zone_col_i is not None:
            filters.extend(
                [
                    CharacterDocument.zone_row_i == zone_row_i,
                    CharacterDocument.zone_col_i == zone_col_i,
                ]
            )

        character_documents = self.alive_query.filter(and_(*filters)).all()

        return [
            self.document_to_model(character_document) for character_document in character_documents
        ]

    def move(
        self, character: CharacterModel, to_world_row: int, to_world_col: int
    ) -> CharacterDocument:
        # TODO BS 2019-06-04: Check if move is possible
        character_document = self.get_document(character.id)
        from_world_row_i = character_document.world_row_i
        from_world_col_i = character_document.world_col_i
        coming_from = get_coming_from(
            before_row_i=character_document.world_row_i,
            before_col_i=character_document.world_col_i,
            after_row_i=to_world_row,
            after_col_i=to_world_col,
        )
        character_document.world_row_i = to_world_row
        character_document.world_col_i = to_world_col
        new_zone_geography = self._kernel.tile_maps_by_position[
            (to_world_row, to_world_col)
        ].source.geography
        new_zone_row_i, new_zone_col_i = get_opposite_zone_place(
            from_=coming_from,
            zone_width=new_zone_geography.width,
            zone_height=new_zone_geography.height,
        )
        character_document.zone_row_i = new_zone_row_i
        character_document.zone_col_i = new_zone_col_i

        self._kernel.message_lib.send_messages_due_to_move(
            character=character,
            from_world_row_i=from_world_row_i,
            from_world_col_i=from_world_col_i,
            to_world_row_i=to_world_row,
            to_world_col_i=to_world_col,
        )
        self.update(character_document)
        return character_document

    def update(self, character_document: CharacterDocument, commit: bool = True) -> None:
        self._kernel.server_db_session.add(character_document)
        if commit:
            self._kernel.server_db_session.commit()

    def get_all_character_count(self) -> int:
        return (
            self._kernel.server_db_session.query(CharacterDocument.id)
            .filter(CharacterDocument.alive == True)
            .count()
        )

    def get_all_character_ids(self) -> typing.Iterable[str]:
        return (
            row[0]
            for row in self._kernel.server_db_session.query(CharacterDocument.id)
            .filter(CharacterDocument.alive == True)
            .all()
        )

    def get_inventory(self, character_id: str) -> CharacterInventoryModel:
        carried_stuff = self._stuff_lib.get_carried_by(character_id, exclude_crafting=False)
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
        for around_row_i, around_col_i in around_character:
            on_same_position_items = self._stuff_lib.get_zone_stuffs(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
            )
            for item in on_same_position_items:
                character_actions_.append(
                    CharacterActionLink(
                        name=f"Jeter un coup d'oeil sur {item.name}",
                        link=DESCRIBE_LOOK_AT_STUFF_URL.format(
                            character_id=character_id, stuff_id=item.id
                        ),
                    )
                )

        # Actions with near ground resources
        for around_row_i, around_col_i in around_character:
            on_same_position_resources = self._kernel.resource_lib.get_ground_resource(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
            )
            for resource in on_same_position_resources:
                character_actions_.append(
                    CharacterActionLink(
                        name=f"Jeter un coup d'oeil sur {resource.name}",
                        link=DESCRIBE_LOOK_AT_RESOURCE_URL.format(
                            character_id=character_id,
                            resource_id=resource.id,
                            row_i=resource.ground_row_i,
                            col_i=resource.ground_col_i,
                        ),
                    )
                )

        # Actions with near build
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
                    name=f"Prendre {stuff.get_name_and_light_description(self._kernel)}",
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

    def get_event(self, event_id: int) -> EventDocument:
        return (
            self._kernel.server_db_session.query(EventDocument)
            .filter(EventDocument.id == event_id)
            .one()
        )

    def get_last_events(
        self, character_id: str, count: int
    ) -> typing.Iterator[CharacterEventModel]:
        for event_doc in (
            self._kernel.server_db_session.query(EventDocument)
            .filter(EventDocument.character_id == character_id)
            .order_by(EventDocument.datetime.desc())
            .limit(count)
        ):
            yield CharacterEventModel(
                id=event_doc.id,
                datetime=event_doc.datetime,
                text=event_doc.text,
                turn=event_doc.turn,
                unread=not event_doc.read,
            )

    def count_story_pages(self, event_id: int) -> int:
        return (
            self._kernel.server_db_session.query(StoryPageDocument)
            .filter(StoryPageDocument.event_id == event_id)
            .count()
        )

    def get_first_story_page(self, event_id: int) -> StoryPage:
        doc = (
            self._kernel.server_db_session.query(StoryPageDocument)
            .filter(StoryPageDocument.event_id == event_id)
            .order_by(StoryPageDocument.id.asc())
            .limit(1)
            .one()
        )
        return self._story_page_doc_to_model(doc)

    def get_story_page(self, story_page_id: int) -> StoryPage:
        doc = (
            self._kernel.server_db_session.query(StoryPageDocument)
            .filter(StoryPageDocument.id == story_page_id)
            .one()
        )
        return self._story_page_doc_to_model(doc)

    def _story_page_doc_to_model(self, story_page_doc: StoryPageDocument) -> StoryPage:
        try:
            previous_page_id = (
                self._kernel.server_db_session.query(StoryPageDocument.id)
                .filter(StoryPageDocument.event_id == story_page_doc.event_id)
                .filter(StoryPageDocument.id < story_page_doc.id)
                .order_by(StoryPageDocument.id.desc())
                .limit(1)
                .scalar()
            )
        except NoResultFound:
            previous_page_id = None

        try:
            next_page_id = (
                self._kernel.server_db_session.query(StoryPageDocument.id)
                .filter(StoryPageDocument.event_id == story_page_doc.event_id)
                .filter(StoryPageDocument.id > story_page_doc.id)
                .order_by(StoryPageDocument.id.asc())
                .limit(1)
                .scalar()
            )
        except NoResultFound:
            next_page_id = None

        image_extension = None
        if story_page_doc.image_id:
            image_extension = (
                self._kernel.server_db_session.query(ImageDocument.extension)
                .filter(ImageDocument.id == story_page_doc.image_id)
                .scalar()
            )

        return StoryPage(
            id=story_page_doc.id,
            event_id=story_page_doc.event_id,
            image_id=story_page_doc.image_id,
            image_extension=image_extension,
            text=story_page_doc.text,
            previous_page_id=previous_page_id,
            next_page_id=next_page_id,
        )

    def add_event(
        self,
        character_id: str,
        title: str,
        story_pages: typing.Optional[typing.List[StoryPageDocument]] = None,
        read: bool = False,
    ) -> EventDocument:
        story_pages = story_pages or []
        turn = self._kernel.universe_lib.get_last_state().turn
        event_doc = EventDocument(character_id=character_id, text=title, turn=turn, read=read)
        self._kernel.server_db_session.add(event_doc)
        self._kernel.server_db_session.commit()
        if story_pages:
            for story_page in story_pages:
                story_page.event_id = event_doc.id
            self.add_story_pages(story_pages)
        return event_doc

    def add_story_pages(self, story_pages: typing.List[StoryPageDocument]) -> None:
        for story_page in story_pages:
            self._kernel.server_db_session.add(story_page)
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
        inventory = self.get_inventory(character_id)
        can_move = True
        cannot_move_reasons: typing.List[str] = []

        if character.action_points < move_cost:
            can_move = False
            cannot_move_reasons.append("Pas assez de Point d'Actions.")

        if character.exhausted:
            can_move = False
            cannot_move_reasons.append("Le personnage est épuisé.")

        if inventory.weight > character.get_weight_capacity(
            self._kernel
        ) or inventory.clutter > character.get_clutter_capacity(self._kernel):
            can_move = False
            cannot_move_reasons.append("Le personnage est surchargé.")

        return MoveZoneInfos(
            can_move=can_move, cost=move_cost, cannot_move_reasons=cannot_move_reasons
        )

    def have_from_of_abilities(
        self, character: CharacterModel, abilities: typing.List[AbilityDescription]
    ) -> typing.List[HaveAbility]:
        around_character = get_on_and_around_coordinates(
            x=character.zone_row_i, y=character.zone_col_i
        )
        haves: typing.List[HaveAbility] = []

        if character.have_one_of_abilities([ability.id for ability in abilities]):
            haves.append(HaveAbility(from_=FromType.CHARACTER, risk=RiskType.NONE))

        for stuff in self._kernel.stuff_lib.get_carried_by(character.id):
            stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                stuff.stuff_id
            )
            if stuff_properties.have_one_of_abilities([ability.id for ability in abilities]):
                haves.append(HaveAbility(from_=FromType.STUFF, risk=RiskType.NONE))

        for around_row_i, around_col_i in around_character:
            for build in self._kernel.build_lib.get_zone_build(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
            ):
                build_description = self._kernel.game.config.builds[build.build_id]
                # FIXME BS 20200220: implement "is working" (with turn consumtion)
                if not build.under_construction:
                    for ability in abilities:
                        if ability.id in build_description.ability_ids:
                            # TODO BS 20200220: implement risks
                            haves.append(HaveAbility(from_=FromType.BUILD, risk=RiskType.NONE))

        return haves

    def kill(self, character_id: str) -> None:
        character_doc = self.get_document(character_id)
        character_doc.alive = False
        for stuff in self._kernel.stuff_lib.get_carried_by(character_id):
            self._kernel.stuff_lib.drop(
                stuff.id,
                world_row_i=character_doc.world_row_i,
                world_col_i=character_doc.world_col_i,
                zone_row_i=character_doc.zone_row_i,
                zone_col_i=character_doc.zone_col_i,
            )

        for carried_resource in self._kernel.resource_lib.get_carried_by(character_id):
            self._kernel.resource_lib.drop(
                character_id=character_id,
                resource_id=carried_resource.id,
                quantity=carried_resource.quantity,
                world_row_i=character_doc.world_row_i,
                world_col_i=character_doc.world_col_i,
                zone_row_i=character_doc.zone_row_i,
                zone_col_i=character_doc.zone_col_i,
            )

        corpse = self._stuff_lib.create_document_from_properties(
            properties=self._kernel.game.stuff_manager.get_stuff_properties_by_id("CORPSE"),
            stuff_id="CORPSE",
            world_row_i=character_doc.world_row_i,
            world_col_i=character_doc.world_col_i,
            zone_row_i=character_doc.zone_row_i,
            zone_col_i=character_doc.zone_col_i,
        )
        self._kernel.stuff_lib.add_stuff(corpse)

        # Remove affinity relations
        self._kernel.server_db_session.query(AffinityRelationDocument).filter(
            AffinityRelationDocument.character_id == character_doc.id
        ).update({"accepted": False, "request": False, "fighter": False})

    def increase_tiredness(self, character_id: str, value: int, commit: bool = True) -> None:
        doc = self.get_document(character_id)

        new_tiredness = doc.tiredness + value
        if new_tiredness > 100:
            new_tiredness = 100
        doc.tiredness = new_tiredness

        if commit:
            self._kernel.server_db_session.add(doc)
            self._kernel.server_db_session.commit()

    def reduce_tiredness(self, character_id: str, value: int, commit: bool = True) -> None:
        doc = self.get_document(character_id)

        new_tiredness = doc.tiredness - value
        if new_tiredness < 0:
            new_tiredness = 0
        doc.tiredness = new_tiredness

        if commit:
            self._kernel.server_db_session.add(doc)
            self._kernel.server_db_session.commit()

    def _get_ready_to_fight_query(
        self, character_ids: typing.List[str], world_row_i: int, world_col_i: int
    ) -> sqlalchemy.orm.Query:
        return self._kernel.character_lib.alive_query.filter(
            CharacterDocument.id.in_(character_ids),
            CharacterDocument.tiredness <= int(MINIMUM_BEFORE_EXHAUSTED),
            CharacterDocument.action_points >= int(FIGHT_AP_CONSUME),
            CharacterDocument.world_row_i == world_row_i,
            CharacterDocument.world_col_i == world_col_i,
        )

    def get_ready_to_fight_count(
        self, character_ids: typing.List[str], world_row_i: int, world_col_i: int
    ) -> int:
        return self._get_ready_to_fight_query(
            character_ids, world_row_i=world_row_i, world_col_i=world_col_i
        ).count()

    def get_ready_to_fights(
        self, character_ids: typing.List[str], world_row_i: int, world_col_i: int
    ) -> typing.List[CharacterModel]:
        return [
            self.document_to_model(doc)
            for doc in self._get_ready_to_fight_query(
                character_ids, world_row_i=world_row_i, world_col_i=world_col_i
            ).all()
        ]

    def reduce_life_points(self, character_id: str, value: float, commit: bool = True) -> float:
        doc = self.get_document(character_id)
        doc.life_points = float(doc.life_points) - value

        if commit:
            self._kernel.server_db_session.add(doc)
            self._kernel.server_db_session.commit()

        return doc.life_points

    def get_with_character_actions(
        self, character: CharacterModel, with_character: CharacterModel
    ) -> typing.List[CharacterActionLink]:
        character_actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name="Voir la fiche",
                link=f"/character/{character.id}/card/{with_character.id}",
                cost=0.0,
            ),
            CharacterActionLink(
                name="Voir l'inventaire",
                link=f"/character/{character.id}/inventory/{with_character.id}",
                cost=0.0,
            ),
            CharacterActionLink(
                name="Voir les conversations",
                link=f"/conversation/{character.id}?with_character_id={with_character.id}",
                cost=0.0,
            ),
            CharacterActionLink(
                name="Démarrer une nouvelle conversation",
                link=f"/conversation/{character.id}/start?with_character_id={with_character.id}",
                cost=0.0,
            ),
            CharacterActionLink(
                name="Faire une proposition commerciale",
                link=f"/business/{character.id}/offers-create?with_character_id={with_character.id}",
                cost=0.0,
            ),
        ]

        for action in self._kernel.action_factory.get_all_with_character_actions():
            try:
                action.check_is_possible(character, with_character=with_character)
                character_actions.extend(
                    action.get_character_actions(character, with_character=with_character)
                )
            except ImpossibleAction:
                pass

        return character_actions
