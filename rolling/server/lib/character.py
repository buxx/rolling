# coding: utf-8
import collections
import datetime
import math
import os
import random
import uuid
import sqlalchemy
from sqlalchemy import Float
from sqlalchemy import and_
from sqlalchemy import cast
from sqlalchemy.orm import Query
from sqlalchemy.orm.exc import NoResultFound
import typing
import slugify

import rrolling
from rolling import util
from rolling.action.base import ActionDescriptionModel
from rolling.action.base import get_with_stuff_action_url
from rolling.action.base import get_with_resource_action_url
from rolling.bonus import Bonus, Bonuses
from rolling.exception import CannotMoveToZoneError
from rolling.exception import ImpossibleAction
from rolling.exception import NotEnoughActionPoints
from rolling.exception import RollingError
from rolling.map.type.property.traversable import traversable_properties
from rolling.model.ability import AbilityDescription
from rolling.model.ability import HaveAbility
from rolling.model.character import CharacterEventModel
from rolling.model.character import CharacterModel
from rolling.model.character import FIGHT_AP_CONSUME
from rolling.model.character import MINIMUM_BEFORE_EXHAUSTED
from rolling.model.data import ItemModel, ListOfItemModel
from rolling.model.event import (
    NewResumeTextData,
    StoryPage,
    WebSocketEvent,
    ZoneEventType,
)
from rolling.model.knowledge import KnowledgeDescription
from rolling.model.meta import FromType
from rolling.model.meta import RiskType
from rolling.model.meta import TransportType
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.skill import CharacterSkillModel
from rolling.model.stuff import CharacterInventoryModel
from rolling.model.stuff import StuffModel
from rolling.model.zone import MoveZoneInfos
from rolling.rolling_types import ActionType
from rolling.server.action import ActionFactory
from rolling.server.controller.url import DESCRIBE_BUILD
from rolling.server.controller.url import DESCRIBE_LOOK_AT_CHARACTER_URL
from rolling.server.controller.url import DESCRIBE_LOOK_AT_RESOURCE_URL
from rolling.server.controller.url import DESCRIBE_LOOK_AT_STUFF_URL
from rolling.server.document.action import AuthorizePendingActionDocument
from rolling.server.document.action import PendingActionDocument
from rolling.server.document.affinity import AffinityDirectionType
from rolling.server.document.affinity import AffinityDocument
from rolling.server.document.affinity import AffinityRelationDocument
from rolling.server.document.affinity import CHIEF_STATUS
from rolling.server.document.base import ImageDocument
from rolling.server.document.business import OfferDocument
from rolling.server.document.character import CharacterDocument
from rolling.server.document.character import FollowCharacterDocument
from rolling.server.document.corpse import AnimatedCorpseType
from rolling.server.document.event import EventDocument
from rolling.server.document.event import StoryPageDocument
from rolling.server.document.knowledge import CharacterKnowledgeDocument
from rolling.server.document.message import MessageDocument
from rolling.server.document.skill import CharacterSkillDocument
from rolling.server.lib.stuff import StuffLib
from rolling.server.link import CharacterActionLink, ExploitableTile
from rolling.server.util import register_image
from rolling.util import character_can_drink_in_its_zone
from rolling.util import filter_action_links
from rolling.util import get_coming_from
from rolling.util import get_on_and_around_coordinates
from rolling.util import get_opposite_zone_place
from rolling.util import get_stuffs_filled_with_resource_id

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel

DEFAULT_LOG_BASE = 4
STARING_LIFE_POINTS = 3.0  # + endurance


class CharacterLib:
    def __init__(
        self, kernel: "Kernel", stuff_lib: typing.Optional[StuffLib] = None
    ) -> None:
        self._kernel = kernel
        self._stuff_lib: StuffLib = stuff_lib or StuffLib(kernel)
        self._action_factory = ActionFactory(kernel)

    @property
    def alive_query(self) -> Query:
        return self._kernel.server_db_session.query(CharacterDocument).filter(
            CharacterDocument.alive == True
        )

    @property
    def alive_query_ids(self) -> Query:
        return self._kernel.server_db_session.query(CharacterDocument.id).filter(
            CharacterDocument.alive == True
        )

    @property
    def dead_query(self) -> Query:
        return self._kernel.server_db_session.query(CharacterDocument).filter(
            CharacterDocument.alive == False
        )

    @property
    def dead_query_ids(self) -> Query:
        return self._kernel.server_db_session.query(CharacterDocument.id).filter(
            CharacterDocument.alive == False
        )

    @property
    def dont_care_alive_query(self) -> Query:
        return self._kernel.server_db_session.query(CharacterDocument)

    def create(
        self,
        name: str,
        skills: typing.Dict[str, float],
        knowledges: typing.List[str],
        spawn_to: typing.Optional[int],
    ) -> str:
        character = CharacterDocument()
        character.id = uuid.uuid4().hex
        character.name = name
        character.type_ = AnimatedCorpseType.CHARACTER.value
        character.max_life_comp = STARING_LIFE_POINTS + skills["endurance"]
        character.life_points = float(character.max_life_comp)
        character.action_points = self._kernel.game.config.start_action_points
        character.max_action_points = self._kernel.game.config.default_maximum_ap
        character.thirst = self._kernel.game.config.start_thirst
        character.hunger = self._kernel.game.config.start_hunger
        character.tracim_password = uuid.uuid4().hex

        # Place on zone
        if spawn_to:
            spawn_point = self._kernel.spawn_point_lib.get_one(spawn_to)
            build_document = self._kernel.build_lib.get_build_doc(spawn_point.build_id)
            world_row_i = build_document.world_row_i
            world_col_i = build_document.world_col_i
            zone_row_i = build_document.zone_row_i
            zone_col_i = build_document.zone_col_i
        else:
            (
                world_row_i,
                world_col_i,
            ) = self._kernel.world_map_source.meta.spawn.get_spawn_coordinates(
                self._kernel.world_map_source
            )
            traversable_coordinates = self._kernel.get_traversable_coordinates(
                world_row_i, world_col_i
            )
            if not traversable_coordinates:
                raise RollingError(
                    f"No traversable coordinate in zone {world_row_i},{world_col_i}"
                )
            zone_row_i, zone_col_i = random.choice(traversable_coordinates)

        character.world_row_i = world_row_i
        character.world_col_i = world_col_i
        character.zone_row_i = zone_row_i
        character.zone_col_i = zone_col_i

        self._kernel.server_db_session.add(character)
        self._kernel.server_db_session.commit()

        for skill_id, skill_value in skills.items():
            self._kernel.server_db_session.add(
                self._kernel.character_lib.create_skill_doc(
                    character.id, skill_id, skill_value
                )
            )
        self._kernel.server_db_session.commit()
        self.ensure_skills_for_character(character.id)

        for knowledge_id in knowledges:
            self._kernel.character_lib.increase_knowledge_progress(
                character.id,
                knowledge_id,
                ap=int(self._kernel.game.config.knowledge[knowledge_id].ap_required),
            )

        self.ensure_skills_for_character(character.id)
        return character.id

    def ensure_skills_for_character(
        self, character_id: str, commit: bool = True
    ) -> None:
        for skill_id, skill_description in self._kernel.game.config.skills.items():
            if (
                not self._kernel.server_db_session.query(CharacterSkillDocument)
                .filter(
                    CharacterSkillDocument.character_id == character_id,
                    CharacterSkillDocument.skill_id == skill_id,
                )
                .count()
            ):
                default_value = skill_description.default
                # find matching counter for default_value
                counter = 1
                while math.log(counter, DEFAULT_LOG_BASE) < default_value:
                    counter += 1

                self._kernel.server_db_session.add(
                    self.create_skill_doc(character_id, skill_id, value=default_value)
                )
        if commit:
            self._kernel.server_db_session.commit()

    def get_document(
        self, id_: str, dead: typing.Optional[bool] = False
    ) -> CharacterDocument:
        if dead is None:
            query = self.dont_care_alive_query
        elif dead:
            query = self.dead_query
        else:
            query = self.alive_query
        return query.filter(CharacterDocument.id == id_).one()

    def get_tracim_account(self, character_id: str) -> rrolling.Account:
        character_doc = self._kernel.character_lib.get_document(character_id)
        assert character_doc.account_id is not None
        account = self._kernel.account_lib.get_account_for_id(character_doc.account_id)
        return rrolling.Account(
            username=rrolling.Username(character_doc.name_slug),
            password=rrolling.Password(character_doc.tracim_password),
            email=rrolling.Email(account.email),
        )

    def get_document_by_name(self, name: str) -> CharacterDocument:
        return self.alive_query.filter(CharacterDocument.name == name).one()

    def document_to_model(
        self, character_document: CharacterDocument
    ) -> CharacterModel:
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

        skills: typing.Dict[str, CharacterSkillModel] = {
            skill_document.skill_id: CharacterSkillModel(
                id=skill_document.skill_id,
                name=self._kernel.game.config.skills[skill_document.skill_id].name,
                value=float(skill_document.value),
                counter=float(skill_document.counter),
            )
            for skill_document in self._kernel.server_db_session.query(
                CharacterSkillDocument
            )
            .filter(CharacterSkillDocument.character_id == character_document.id)
            .all()
        }
        knowledges: typing.Dict[str, KnowledgeDescription] = {
            row[0]: self._kernel.game.config.knowledge[row[0]]
            for row in self._kernel.server_db_session.query(
                CharacterKnowledgeDocument.knowledge_id,
                CharacterKnowledgeDocument.acquired,
            )
            .filter(CharacterKnowledgeDocument.character_id == character_document.id)
            .all()
            if row[1]
        }

        ability_ids = []
        for knowledge_description in knowledges.values():
            ability_ids.extend(knowledge_description.abilities)
        ability_ids = list(set(ability_ids))

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
            hunting_and_collecting_comp=float(
                character_document.hunting_and_collecting_comp
            ),
            find_water_comp=float(character_document.find_water_comp),
            thirst=character_document.thirst,
            hunger=character_document.hunger,
            tiredness=character_document.tiredness,
            action_points=float(character_document.action_points),
            max_action_points=float(character_document.max_action_points),
            bags=[
                self._stuff_lib.stuff_model_from_doc(bag_doc)
                for bag_doc in character_document.used_as_bag
            ],
            weapon=weapon,
            shield=shield,
            armor=armor,
            skills=skills,
            knowledges=knowledges,
            ability_ids=ability_ids,
            alive=character_document.alive,
            avatar_uuid=character_document.avatar_uuid,
            avatar_is_validated=character_document.avatar_is_validated,
            tracim_user_id=character_document.tracim_user_id,
            tracim_home_space_id=character_document.tracim_home_space_id,
            tracim_password=character_document.tracim_password,
        )

    def get_multiple(
        self, character_ids: typing.List[str]
    ) -> typing.List[CharacterModel]:
        return [
            self.document_to_model(doc)
            for doc in self.alive_query.filter(
                CharacterDocument.id.in_(character_ids)
            ).all()
        ]

    def get(
        self,
        id_: str,
        compute_unread_event: bool = False,
        compute_unread_zone_message: bool = False,
        compute_unread_conversation: bool = False,
        compute_unvote_affinity_relation: bool = False,
        compute_unread_transactions: bool = False,
        compute_pending_actions: bool = False,
        compute_with_fighters: bool = False,
        dead: typing.Optional[bool] = None,
    ) -> CharacterModel:
        character_document = self.get_document(id_, dead=dead)
        model = self.document_to_model(character_document)

        # TODO BS: Move these compute unread/unvote in respective libs
        if (
            compute_unread_event
            and self._kernel.server_db_session.query(EventDocument.id)
            .filter(
                and_(EventDocument.character_id == id_, EventDocument.read == False)
            )
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
                for r in self._kernel.server_db_session.query(
                    AffinityRelationDocument.affinity_id
                )
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
                    AffinityDocument.direction_type.in_(
                        [AffinityDirectionType.ONE_DIRECTOR.value]
                    ),
                )
                .all()
            ]
            if (
                self._kernel.server_db_session.query(AffinityRelationDocument)
                .filter(
                    AffinityRelationDocument.affinity_id.in_(
                        character_chief_affinity_ids
                    ),
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

        if compute_pending_actions:
            model.pending_actions = self.get_pending_actions_count(
                character_document.id
            )

        if compute_with_fighters:
            model.with_fighters_count = self.get_with_fighters_count(
                character_document.id
            )

        model.is_hunger = model.hunger > self._kernel.game.config.stop_auto_eat_hunger
        model.is_thirsty = (
            model.thirst > self._kernel.game.config.stop_auto_drink_thirst
        )

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

    def _get_zone_characters_query(
        self,
        row_i: int,
        col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
        exclude_ids: typing.Optional[typing.List[str]] = None,
    ) -> Query:
        exclude_ids = exclude_ids or []
        filters = [
            CharacterDocument.world_row_i == row_i,
            CharacterDocument.world_col_i == col_i,
        ]

        if exclude_ids:
            filters.extend([CharacterDocument.id.notin_(exclude_ids)])

        if zone_row_i is not None and zone_col_i is not None:
            filters.extend(
                [
                    CharacterDocument.zone_row_i == zone_row_i,
                    CharacterDocument.zone_col_i == zone_col_i,
                ]
            )

        return self.alive_query.filter(and_(*filters))

    def get_zone_characters(
        self,
        row_i: int,
        col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
        exclude_ids: typing.Optional[typing.List[str]] = None,
    ) -> typing.List[CharacterModel]:
        character_documents = self._get_zone_characters_query(
            row_i=row_i,
            col_i=col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
            exclude_ids=exclude_ids,
        ).all()
        return [
            self.document_to_model(character_document)
            for character_document in character_documents
        ]

    def count_zone_characters(
        self,
        row_i: int,
        col_i: int,
        zone_row_i: typing.Optional[int] = None,
        zone_col_i: typing.Optional[int] = None,
        exclude_ids: typing.Optional[typing.List[str]] = None,
    ) -> int:
        return self._get_zone_characters_query(
            row_i=row_i,
            col_i=col_i,
            zone_row_i=zone_row_i,
            zone_col_i=zone_col_i,
            exclude_ids=exclude_ids,
        ).count()

    async def move(
        self,
        character: CharacterModel,
        to_world_row: int,
        to_world_col: int,
        commit: bool = True,
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

        # FIXME BS NOW: walking or something else
        def get_walking_coordinates(
            origin_new_zone_row_i: int, origin_new_zone_col_i: int
        ):
            if traversable_properties[
                new_zone_geography.rows[origin_new_zone_row_i][origin_new_zone_col_i]
            ].get(TransportType.WALKING.value):
                return origin_new_zone_row_i, origin_new_zone_col_i

            distances = [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
            ]  # after 10 of distance ... it is a fail
            for distance in distances:
                for (
                    new_zone_row_i_,
                    new_zone_col_i_,
                ) in util.get_on_and_around_coordinates(
                    origin_new_zone_row_i,
                    origin_new_zone_col_i,
                    distance=distance,
                    exclude_on=True,
                ):
                    if new_zone_row_i_ < 0:
                        new_zone_row_i_ = 0
                    if new_zone_col_i_ < 0:
                        new_zone_col_i_ = 0

                    try:
                        if traversable_properties[
                            new_zone_geography.rows[new_zone_row_i_][new_zone_col_i_]
                        ].get(TransportType.WALKING.value):
                            return new_zone_row_i_, new_zone_col_i_
                    except KeyError:
                        pass

            return origin_new_zone_row_i, origin_new_zone_col_i

        new_zone_row_i, new_zone_col_i = get_walking_coordinates(
            new_zone_row_i, new_zone_col_i
        )
        character_document.zone_row_i = new_zone_row_i
        character_document.zone_col_i = new_zone_col_i

        await self._kernel.message_lib.send_messages_due_to_move(
            character=character,
            from_world_row_i=from_world_row_i,
            from_world_col_i=from_world_col_i,
            to_world_row_i=to_world_row,
            to_world_col_i=to_world_col,
        )

        # Update door rules in left zone
        await self._kernel.door_lib.trigger_character_left_zone(
            world_row_i=from_world_row_i,
            world_col_i=from_world_col_i,
            character_id=character_document.id,
        )

        self.update(character_document)

        # Update door rules in new zone
        await self._kernel.door_lib.trigger_character_enter_in_zone(
            world_row_i=to_world_row,
            world_col_i=to_world_col,
            character_id=character_document.id,
        )

        if commit:
            self._kernel.server_db_session.commit()

        return character_document

    def update(
        self, character_document: CharacterDocument, commit: bool = True
    ) -> None:
        self._kernel.server_db_session.add(character_document)
        if commit:
            self._kernel.server_db_session.commit()

    def get_all_character_count(self) -> int:
        return (
            self._kernel.server_db_session.query(CharacterDocument.id)
            .filter(CharacterDocument.alive == True)
            .count()
        )

    def get_all_character_ids(self, alive: bool = True) -> typing.Iterable[str]:
        return (
            row[0]
            for row in self._kernel.server_db_session.query(CharacterDocument.id)
            .filter(CharacterDocument.alive == alive)
            .all()
        )

    def get_inventory(
        self, character: CharacterModel, include_equip: bool = True
    ) -> CharacterInventoryModel:
        carried_stuff = self._stuff_lib.get_carried_by(
            character.id, exclude_crafting=False, include_equip=include_equip
        )
        carried_resources = self._kernel.resource_lib.get_carried_by(character.id)

        total_weight = sum([stuff.weight for stuff in carried_stuff if stuff.weight])
        total_weight += sum([r.weight for r in carried_resources if r.weight])

        total_clutter = sum(
            [
                stuff.clutter
                for stuff in carried_stuff
                if stuff.clutter and not stuff.used_by
            ]
        )
        total_clutter += sum([r.clutter for r in carried_resources if r.clutter])

        return CharacterInventoryModel(
            stuff=carried_stuff,
            resource=carried_resources,
            weight=total_weight,
            clutter=total_clutter,
            over_weight=total_weight > character.get_weight_capacity(self._kernel),
            over_clutter=total_clutter > character.get_clutter_capacity(self._kernel),
        )

    def get_on_place_stuff_actions(
        self,
        character: CharacterModel,
        quick_actions: bool = False,
        filter_action_types: typing.Optional[typing.List[str]] = None,
    ) -> typing.Generator[CharacterActionLink, None, None]:
        if (
            filter_action_types is not None
            and ActionType.TAKE_STUFF.value not in filter_action_types
        ):
            return

        around_character = get_on_and_around_coordinates(
            x=character.zone_row_i, y=character.zone_col_i
        )

        if quick_actions:
            stuffs_by_type: typing.DefaultDict[
                str, typing.List[StuffModel]
            ] = collections.defaultdict(list)
            for around_row_i, around_col_i in around_character:
                for stuff in self._stuff_lib.get_zone_stuffs(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=around_row_i,
                    zone_col_i=around_col_i,
                ):
                    stuffs_by_type[stuff.stuff_id].append(stuff)

            for stuff_id, stuffs in stuffs_by_type.items():
                stuff_description = (
                    self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
                )
                yield CharacterActionLink(
                    name=f"Ramasser {stuffs[0].stuff_id}",
                    link=get_with_stuff_action_url(
                        character_id=character.id,
                        stuff_id=stuffs[0].id,
                        action_type=ActionType.TAKE_STUFF,
                        action_description_id="TAKE_STUFF",
                        query_params={
                            "quantity": len(stuffs),
                            "quick_action": "1",
                            "explode_take": "1",
                        },
                    ),
                    classes1=["TAKE"],
                    classes2=stuff_description.classes + [stuff_description.id],
                )
            return

        for around_row_i, around_col_i in around_character:
            on_same_position_items = self._stuff_lib.get_zone_stuffs(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
            )
            for item in on_same_position_items:
                yield CharacterActionLink(
                    name=f"Jeter un coup d'oeil sur {item.name}",
                    link=DESCRIBE_LOOK_AT_STUFF_URL.format(
                        character_id=character.id, stuff_id=item.id
                    ),
                    group_name="Voir les objets et bâtiments autour",
                )

    def get_on_place_resource_actions(
        self,
        character: CharacterModel,
        quick_actions: bool = False,
        filter_action_types: typing.Optional[typing.List[str]] = None,
    ) -> typing.Generator[CharacterActionLink, None, None]:
        if (
            filter_action_types is not None
            and ActionType.TAKE_RESOURCE.value not in filter_action_types
        ):
            return

        around_character = get_on_and_around_coordinates(
            x=character.zone_row_i, y=character.zone_col_i
        )

        if quick_actions:
            resources_quantity_by_ids: typing.DefaultDict[
                str, float
            ] = collections.defaultdict(lambda: 0.0)
            for around_row_i, around_col_i in around_character:
                for resource_on_ground in self._kernel.resource_lib.get_ground_resource(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=around_row_i,
                    zone_col_i=around_col_i,
                ):
                    resources_quantity_by_ids[
                        resource_on_ground.id
                    ] += resource_on_ground.quantity

            for resource_id, quantity in resources_quantity_by_ids.items():
                resource_description = self._kernel.game.config.resources[resource_id]
                yield CharacterActionLink(
                    name=f"Ramasser {resource_id}",
                    link=get_with_resource_action_url(
                        character_id=character.id,
                        resource_id=resource_id,
                        action_type=ActionType.TAKE_RESOURCE,
                        action_description_id="TAKE_RESOURCE",
                        query_params={
                            "quantity": quantity,
                            "quick_action": "1",
                            "explode_take": "1",
                        },
                    ),
                    classes1=["TAKE"],
                    classes2=[resource_description.id],
                )
            return

        for around_row_i, around_col_i in around_character:
            on_same_position_resources = self._kernel.resource_lib.get_ground_resource(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
            )
            for resource in on_same_position_resources:
                yield CharacterActionLink(
                    name=f"Jeter un coup d'oeil sur {resource.name}",
                    link=DESCRIBE_LOOK_AT_RESOURCE_URL.format(
                        character_id=character.id,
                        resource_id=resource.id,
                        row_i=resource.ground_row_i,
                        col_i=resource.ground_col_i,
                    ),
                    group_name="Voir les objets et bâtiments autour",
                )

    def get_on_place_build_actions(
        self,
        character: CharacterModel,
        only_quick_actions: bool = False,
        filter_action_types: typing.Optional[typing.List[str]] = None,
    ) -> typing.List[CharacterActionLink]:
        around_coordinates = get_on_and_around_coordinates(
            x=character.zone_row_i, y=character.zone_col_i
        )
        character_actions_: typing.List[CharacterActionLink] = []

        builds = []
        for around_row_i, around_col_i in around_coordinates:
            builds.extend(
                self._kernel.build_lib.get_zone_build(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=around_row_i,
                    zone_col_i=around_col_i,
                    is_floor=False,
                )
            )

        for build in builds:
            if only_quick_actions:
                character_actions_.extend(
                    self._kernel.build_lib.get_on_build_actions(
                        character=character,
                        build_id=build.id,
                        only_quick_actions=True,
                        filter_action_types=filter_action_types,
                    )
                )

        if filter_action_types is None and builds:
            character_actions_.append(
                CharacterActionLink(
                    name=f"Détails d'un bâtiment",
                    link=f"/character/{character.id}/look-build-from-quick-action",
                    group_name="Voir",
                    classes1=["LOOK"],
                    exploitable_tiles=[
                        ExploitableTile(
                            zone_row_i=build.zone_row_i,
                            zone_col_i=build.zone_col_i,
                            classes=[],
                        )
                        for build in builds
                    ],
                )
            )

        return character_actions_

    def get_from_inventory_actions(
        self,
        character: CharacterModel,
        filter_action_types: typing.Optional[typing.List[str]] = None,
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []

        for resource in self._kernel.resource_lib.get_carried_by(character.id):
            actions.extend(
                self._kernel.character_lib.get_on_resource_actions(
                    character_id=character.id,
                    resource_id=resource.id,
                    for_actions_page=True,
                    filter_action_types=filter_action_types,
                )
            )

        for stuff in self._kernel.stuff_lib.get_carried_by(
            character.id, exclude_crafting=False
        ):
            actions.extend(
                self._kernel.stuff_lib.get_carrying_actions(
                    character=character,
                    stuff=stuff,
                    for_actions_page=True,
                    filter_action_types=filter_action_types,
                )
            )

        return actions

    def get_on_place_character_actions(
        self,
        character: CharacterModel,
        filter_action_types: typing.Optional[typing.List[str]] = None,
    ) -> typing.List[CharacterActionLink]:
        if filter_action_types is not None:
            return []

        around_character = get_on_and_around_coordinates(
            x=character.zone_row_i, y=character.zone_col_i
        )
        character_actions_: typing.List[CharacterActionLink] = []

        for around_row_i, around_col_i in around_character:
            on_same_position_characters = self.get_zone_characters(
                row_i=character.world_row_i,
                col_i=character.world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
                exclude_ids=[character.id],
            )
            for item in on_same_position_characters:
                character_actions_.append(
                    CharacterActionLink(
                        name=f"{item.name}",
                        link=DESCRIBE_LOOK_AT_CHARACTER_URL.format(
                            character_id=character.id, with_character_id=item.id
                        ),
                    )
                )

        return character_actions_

    def _add_category_to_action_links(
        self,
        action_links: typing.List[CharacterActionLink],
        category: str,
        only_if_none: bool = True,
    ) -> typing.List[CharacterActionLink]:
        for action_link in action_links:
            if not only_if_none or (only_if_none and action_link.category is None):
                action_link.category = category
        return action_links

    def get_on_place_actions(
        self,
        character_id: str,
        quick_actions_only: bool = False,
        filter_action_types: typing.Optional[typing.List[str]] = None,
    ) -> typing.List[CharacterActionLink]:
        character = self.get(character_id)
        character_actions_: typing.List[CharacterActionLink] = []

        if not quick_actions_only:
            character_actions_.extend(
                self._add_category_to_action_links(
                    list(
                        self.get_on_place_stuff_actions(
                            character,
                            filter_action_types=filter_action_types,
                        )
                    ),
                    "Objets, ressources et bâtiments autour",
                )
            )

        if not quick_actions_only:
            character_actions_.extend(
                self._add_category_to_action_links(
                    list(
                        self.get_on_place_resource_actions(
                            character,
                            filter_action_types=filter_action_types,
                        )
                    ),
                    "Objets, ressources et bâtiments autour",
                )
            )

        if not quick_actions_only:
            character_actions_.extend(
                self._add_category_to_action_links(
                    self.get_on_place_build_actions(
                        character,
                        filter_action_types=filter_action_types,
                    ),
                    "Objets, ressources et bâtiments autour",
                )
            )
        else:
            character_actions_.extend(
                self.get_on_place_build_actions(
                    character,
                    only_quick_actions=True,
                    filter_action_types=filter_action_types,
                )
            )

        if not quick_actions_only:
            character_actions_.extend(
                self._add_category_to_action_links(
                    self.get_on_place_character_actions(
                        character,
                        filter_action_types=filter_action_types,
                    ),
                    "Personnages",
                )
            )

        if not quick_actions_only:
            character_actions_.extend(
                self._add_category_to_action_links(
                    self.get_from_inventory_actions(
                        character,
                        filter_action_types=filter_action_types,
                    ),
                    "Inventaire",
                )
            )

        # Actions with available character actions
        for action in self._action_factory.get_all_character_actions(
            filter_action_types=filter_action_types,
        ):
            if not quick_actions_only:
                character_actions_.extend(
                    self._add_category_to_action_links(
                        action.get_character_actions(character), "Divers"
                    )
                )
            else:
                character_actions_.extend(action.get_quick_actions(character))

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
                    link=get_with_stuff_action_url(
                        character_id=character_id,
                        stuff_id=stuff_id,
                        action_type=ActionType.TAKE_STUFF,
                        action_description_id="TAKE_STUFF",
                        query_params={},
                    ),
                )
            )
        elif stuff.carried_by == character_id:
            character_actions.extend(
                self._stuff_lib.get_carrying_actions(character, stuff)
            )

        return filter_action_links(character_actions)

    def get_on_resource_actions(
        self,
        character_id: str,
        resource_id: str,
        for_actions_page: bool = False,
        filter_action_types: typing.Optional[typing.List[str]] = None,
    ) -> typing.List[CharacterActionLink]:
        character = self.get(character_id)
        character_actions = self._kernel.resource_lib.get_carrying_actions(
            character,
            resource_id,
            for_actions_page=for_actions_page,
            filter_action_types=filter_action_types,
        )
        return filter_action_links(character_actions)

    def take_stuff(self, character_id: str, stuff_id: int) -> None:
        self._stuff_lib.set_carried_by(stuff_id=stuff_id, character_id=character_id)

    def mark_event_as_read(self, event_ids: typing.List[int]) -> None:
        self._kernel.server_db_session.query(EventDocument).filter(
            EventDocument.id.in_(event_ids)
        ).update({"read": True}, synchronize_session="fetch")
        self._kernel.server_db_session.commit()

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
        message: str,
    ) -> None:
        character_doc = self.get_document(character_id)
        rrolling.Dealer(self._kernel.server_config.tracim_config).create_publication(
            rrolling.SpaceId(character_doc.tracim_home_space_id),
            title,
            message,
        )

    def get_used_bags(self, character_id: str) -> typing.List[StuffModel]:
        return self._stuff_lib.get_carried_and_used_bags(character_id)

    async def reduce_action_points(
        self, character_id: str, cost: float, commit: bool = True, check: bool = False
    ) -> CharacterDocument:
        character_doc = self.get_document(character_id)

        if check and character_doc.action_points < cost:
            raise NotEnoughActionPoints(cost)

        character_doc.action_points = float(character_doc.action_points) - cost
        self._kernel.server_db_session.add(character_doc)

        if commit:
            self._kernel.server_db_session.commit()

        await self.refresh_character(character_doc)
        return character_doc

    def get_move_to_zone_infos(
        self, character_id: str, world_row_i: int, world_col_i: int
    ) -> MoveZoneInfos:
        try:
            zone_type = self._kernel.world_map_source.geography.rows[world_row_i][
                world_col_i
            ]
        except IndexError:
            raise ImpossibleAction("Mouvement impossible (hors du monde)")
        move_cost = self._kernel.game.world_manager.get_zone_properties(
            zone_type
        ).move_cost
        character = self.get(character_id)
        inventory = self.get_inventory(character)
        can_move = True
        cannot_move_reasons: typing.List[str] = []

        if character.action_points < move_cost:
            can_move = False
            cannot_move_reasons.append("Pas assez de Point d'Actions.")

        if character.is_exhausted:
            can_move = False
            cannot_move_reasons.append("Le personnage est épuisé.")

        if inventory.weight > character.get_weight_capacity(
            self._kernel
        ) or inventory.clutter > character.get_clutter_capacity(self._kernel):
            can_move = False
            cannot_move_reasons.append("Le personnage est surchargé.")

        try:
            self.check_can_move_to_zone(world_row_i, world_col_i, character)
        except CannotMoveToZoneError as exc:
            can_move = False
            cannot_move_reasons.append(str(exc))

        followers_can = []
        followers_cannot = []
        followers_discreetly_can = []
        followers_discreetly_cannot = []
        for follow, follower in self._kernel.character_lib.get_follower(
            character_id, row_i=character.world_row_i, col_i=character.world_col_i
        ):
            transport_type_ok = True
            try:
                self.check_can_move_to_zone(world_row_i, world_col_i, follower)
            except CannotMoveToZoneError:
                transport_type_ok = False
            follower_inventory = self.get_inventory(follower)
            if (
                follower_inventory.weight > follower.get_weight_capacity(self._kernel)
                or follower_inventory.clutter
                > follower.get_clutter_capacity(self._kernel)
                or follower.is_exhausted
                or follower.action_points < move_cost
                or not transport_type_ok
            ):
                if follow.discreetly:
                    followers_discreetly_cannot.append(follower)
                else:
                    followers_cannot.append(follower)
            else:
                if follow.discreetly:
                    followers_discreetly_can.append(follower)
                else:
                    followers_can.append(follower)

        return MoveZoneInfos(
            can_move=can_move,
            cost=move_cost,
            cannot_move_reasons=cannot_move_reasons,
            followers_can=followers_can,
            followers_cannot=followers_cannot,
            followers_discreetly_can=followers_discreetly_can,
            followers_discreetly_cannot=followers_discreetly_cannot,
        )

    def have_from_of_abilities(
        self, character: CharacterModel, abilities: typing.List[AbilityDescription]
    ) -> typing.List[HaveAbility]:
        around_character = get_on_and_around_coordinates(
            x=character.zone_row_i, y=character.zone_col_i
        )
        haves: typing.List[HaveAbility] = []

        for have_ability_id in character.have_abilities(
            [ability.id for ability in abilities]
        ):
            haves.append(
                HaveAbility(
                    ability_id=have_ability_id,
                    from_=FromType.HIMSELF,
                    risk=RiskType.NONE,
                )
            )

        carried_or_around_stuffs = self._kernel.stuff_lib.get_carried_by(character.id)
        for row_i, col_i in around_character:
            # FIXME BS : optimize by permitting give list of coordinates
            carried_or_around_stuffs += self._kernel.stuff_lib.get_zone_stuffs(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=row_i,
                zone_col_i=col_i,
            )
        for stuff in carried_or_around_stuffs:
            stuff_properties = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                    stuff.stuff_id
                )
            )
            for have_ability_id in stuff_properties.have_abilities(
                [ability.id for ability in abilities]
            ):
                haves.append(
                    HaveAbility(
                        ability_id=have_ability_id,
                        from_=FromType.STUFF,
                        risk=RiskType.NONE,
                    )
                )

        for around_row_i, around_col_i in around_character:
            for build in self._kernel.build_lib.get_zone_build(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=around_row_i,
                zone_col_i=around_col_i,
            ):
                build_description = self._kernel.game.config.builds[build.build_id]
                if not build.under_construction and (
                    (build_description.abilities_if_is_on and build.is_on)
                    or (not build_description.abilities_if_is_on)
                ):
                    for ability in abilities:
                        if ability.id in build_description.ability_ids:
                            # TODO BS 20200220: implement risks
                            haves.append(
                                HaveAbility(
                                    ability_id=ability.id,
                                    from_=FromType.BUILD,
                                    risk=RiskType.NONE,
                                )
                            )

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
            properties=self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                "CORPSE"
            ),
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

    def increase_tiredness(
        self, character_id: str, value: int, commit: bool = True
    ) -> None:
        doc = self.get_document(character_id)

        new_tiredness = doc.tiredness + value
        if new_tiredness > 100:
            new_tiredness = 100
        doc.tiredness = new_tiredness

        if commit:
            self._kernel.server_db_session.add(doc)
            self._kernel.server_db_session.commit()

    def reduce_tiredness(
        self, character_id: str, value: int, commit: bool = True
    ) -> int:
        doc = self.get_document(character_id)

        new_tiredness = doc.tiredness - value
        if new_tiredness < 0:
            new_tiredness = 0
        doc.tiredness = new_tiredness

        if commit:
            self._kernel.server_db_session.add(doc)
            self._kernel.server_db_session.commit()

        return new_tiredness

    def _get_ready_to_fight_query(
        self, character_ids: typing.List[str], world_row_i: int, world_col_i: int
    ) -> sqlalchemy.orm.Query:
        return self._kernel.character_lib.alive_query.filter(
            CharacterDocument.id.in_(character_ids),
            cast(CharacterDocument.tiredness, Float) <= int(MINIMUM_BEFORE_EXHAUSTED),
            cast(CharacterDocument.action_points, Float) >= int(FIGHT_AP_CONSUME),
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

    def reduce_life_points(
        self, character_id: str, value: float, commit: bool = True
    ) -> float:
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
                name="Conversation (page web)",
                link=f"{self._kernel.server_config.base_url}/conversation/{character.id}/web/setup?character_id={character.id}&character_id={with_character.id}",
                cost=0.0,
                is_web_browser_link=True,
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
                    action.get_character_actions(
                        character, with_character=with_character
                    )
                )
            except ImpossibleAction:
                pass

        return character_actions

    def create_skill_doc(
        self, character_id: str, skill_id: str, value: float
    ) -> CharacterSkillDocument:
        # find matching counter for default_value
        counter = 1
        while math.log(counter, DEFAULT_LOG_BASE) < value:
            counter += 1

        return CharacterSkillDocument(
            skill_id=skill_id,
            character_id=character_id,
            value=str(value),
            counter=counter,
        )

    def increase_skill(
        self, character_id: str, skill_id: str, increment: float, commit: bool = True
    ) -> None:
        skill_doc: CharacterSkillDocument = (
            self._kernel.server_db_session.query(CharacterSkillDocument)
            .filter(
                CharacterSkillDocument.character_id == character_id,
                CharacterSkillDocument.skill_id == skill_id,
            )
            .one()
        )
        counter_as_int_before = int(skill_doc.counter)
        skill_doc.counter += increment
        if counter_as_int_before != int(skill_doc.counter):
            skill_doc.value = math.log(skill_doc.counter, DEFAULT_LOG_BASE)

        self._kernel.server_db_session.add(skill_doc)
        if commit:
            self._kernel.server_db_session.commit()

    def get_health_text(self, character: CharacterModel) -> str:
        health = "Ok"
        if character.life_points < self._kernel.game.config.less_than_is_health2:
            health = "Moyen"
        if character.life_points < self._kernel.game.config.less_than_is_health3:
            health = "Mauvais"
        if character.life_points < self._kernel.game.config.less_than_is_health4:
            health = "Critique"
        return health

    def get_resume_text(self, character_id: str) -> typing.List[ItemModel]:
        character = self.get(character_id)
        followers_count = self.get_follower_count(
            character_id, row_i=character.world_row_i, col_i=character.world_col_i
        )
        following_count = self.get_followed_count(
            character_id, row_i=character.world_row_i, col_i=character.world_col_i
        )

        can_drink_str = "Non"
        if character_can_drink_in_its_zone(self._kernel, character):
            can_drink_str = "Oui"
        else:
            drinkable_stuffs = get_stuffs_filled_with_resource_id(
                self._kernel,
                character_id,
                self._kernel.game.config.fresh_water_resource_id,
            )
            total_drinkable_value = sum(s.filled_value or 0.0 for s in drinkable_stuffs)
            if total_drinkable_value:
                drink_action_description = (
                    self._kernel.game.get_drink_water_action_description()
                )
                drinkable_ticks = (
                    total_drinkable_value
                    // drink_action_description.properties["consume_per_tick"]
                )
                if (
                    drinkable_ticks
                    > self._kernel.game.config.limit_warning_drink_left_tick
                ):
                    can_drink_str = "Oui"
                else:
                    can_drink_str = "Faible"

        can_eat_str = "Non"
        eatables = self.get_eatables(character)
        eatables_total_ticks = 0
        for carried_eatable, carried_action_description in eatables:
            eatable_total_ticks = (
                carried_eatable.quantity
                // carried_action_description.properties["consume_per_tick"]
            )
            eatables_total_ticks += eatable_total_ticks
        if eatables_total_ticks:
            can_eat_str = "Faible"
            if (
                eatables_total_ticks
                > self._kernel.game.config.limit_warning_eat_left_tick
            ):
                can_eat_str = "Oui"

        fighter_with_him = self._kernel.character_lib.get_with_fighters_count(
            character_id
        )

        hunger_class = "green"
        thirst_class = "green"
        tiredness_class = "green"

        if (
            character.hunger
            >= self._kernel.game.config.limit_hunger_increase_life_point
        ):
            hunger_class = "red"
        elif character.hunger >= self._kernel.game.config.stop_auto_eat_hunger:
            hunger_class = "yellow"

        if (
            character.thirst
            >= self._kernel.game.config.limit_thirst_increase_life_point
        ):
            thirst_class = "red"
        elif character.thirst >= self._kernel.game.config.stop_auto_drink_thirst:
            thirst_class = "yellow"

        if character.is_exhausted:
            tiredness_class = "red"
        elif character.tired:
            tiredness_class = "yellow"

        unread_messages = rrolling.Dealer(
            self._kernel.server_config.tracim_config
        ).get_unread_messages_count(rrolling.AccountId(character.tracim_user_id))

        return [
            ItemModel(
                "PV", value_is_str=True, value_str=self.get_health_text(character)
            ),
            ItemModel(
                "PA", value_is_float=True, value_float=round(character.action_points, 1)
            ),
            ItemModel(
                "Faim",
                value_is_float=True,
                value_float=round(character.hunger, 0),
                classes=["inverted_percent", hunger_class],
            ),
            ItemModel(
                "Soif",
                value_is_float=True,
                value_float=round(character.thirst, 0),
                classes=["inverted_percent", thirst_class],
            ),
            ItemModel(
                "Fatigue",
                value_is_float=True,
                value_float=round(character.tiredness, 0),
                classes=["inverted_percent", tiredness_class],
            ),
            ItemModel("A boire", value_is_str=True, value_str=can_drink_str),
            ItemModel("A manger", value_is_str=True, value_str=can_eat_str),
            ItemModel(
                "Suivis", value_is_float=True, value_float=float(following_count)
            ),
            ItemModel(
                "Suiveurs", value_is_float=True, value_float=float(followers_count)
            ),
            ItemModel(
                "Combattants", value_is_float=True, value_float=float(fighter_with_him)
            ),
            ItemModel(
                "Messages", value_is_float=True, value_float=float(unread_messages)
            ),
        ]

    def is_following(
        self,
        follower_id: str,
        followed_id: str,
        discreetly: typing.Optional[bool] = None,
    ) -> bool:
        query = self._kernel.server_db_session.query(FollowCharacterDocument).filter(
            FollowCharacterDocument.follower_id == follower_id,
            FollowCharacterDocument.followed_id == followed_id,
        )

        if discreetly is not None:
            query = query.filter(FollowCharacterDocument.discreetly == discreetly)

        return bool(query.count())

    def get_follower_query(
        self,
        followed_id: str,
        discreetly: typing.Optional[bool] = None,
        row_i: typing.Optional[int] = None,
        col_i: typing.Optional[int] = None,
    ) -> Query:
        query = self._kernel.server_db_session.query(FollowCharacterDocument).filter(
            FollowCharacterDocument.followed_id == followed_id
        )

        if discreetly is not None:
            query = query.filter(FollowCharacterDocument.discreetly == discreetly)

        if row_i is not None and col_i is not None:
            here_ids = self.get_zone_character_ids(row_i, col_i)
            query = query.filter(FollowCharacterDocument.follower_id.in_(here_ids))

        return query

    def get_followed_query(
        self,
        follower_id: str,
        discreetly: typing.Optional[bool] = None,
        row_i: typing.Optional[int] = None,
        col_i: typing.Optional[int] = None,
    ) -> Query:
        query = self._kernel.server_db_session.query(FollowCharacterDocument).filter(
            FollowCharacterDocument.follower_id == follower_id
        )

        if discreetly is not None:
            query = query.filter(FollowCharacterDocument.discreetly == discreetly)

        if row_i is not None and col_i is not None:
            here_ids = self.get_zone_character_ids(row_i, col_i)
            query = query.filter(FollowCharacterDocument.followed_id.in_(here_ids))

        return query

    def get_follower(
        self,
        followed_id: str,
        discreetly: typing.Optional[bool] = None,
        row_i: typing.Optional[int] = None,
        col_i: typing.Optional[int] = None,
    ) -> typing.List[typing.Tuple[FollowCharacterDocument, CharacterModel]]:
        query = self.get_follower_query(
            followed_id, discreetly, row_i=row_i, col_i=col_i
        )
        follows = [r for r in query.all()]
        follows_by_id = {f.follower_id: f for f in follows}

        return [
            (follows_by_id[doc.id], self.document_to_model(doc))
            for doc in self.alive_query.filter(
                CharacterDocument.id.in_(follows_by_id.keys())
            ).all()
        ]

    def get_follower_count(
        self,
        followed_id: str,
        discreetly: typing.Optional[bool] = None,
        row_i: typing.Optional[int] = None,
        col_i: typing.Optional[int] = None,
    ) -> int:
        return self.get_follower_query(
            followed_id, discreetly, row_i=row_i, col_i=col_i
        ).count()

    def get_followed(
        self,
        follower_id: str,
        discreetly: typing.Optional[bool] = None,
        row_i: typing.Optional[int] = None,
        col_i: typing.Optional[int] = None,
    ) -> typing.List[typing.Tuple[FollowCharacterDocument, CharacterModel]]:
        query = self.get_followed_query(
            follower_id, discreetly, row_i=row_i, col_i=col_i
        )
        follows = [r for r in query.all()]
        follows_by_id = {f.followed_id: f for f in follows}

        return [
            (follows_by_id[doc.id], self.document_to_model(doc))
            for doc in self.alive_query.filter(
                CharacterDocument.id.in_(follows_by_id.keys())
            ).all()
        ]

    def get_followed_count(
        self,
        follower_id: str,
        discreetly: typing.Optional[bool] = None,
        row_i: typing.Optional[int] = None,
        col_i: typing.Optional[int] = None,
    ) -> int:
        return self.get_followed_query(
            follower_id, discreetly, row_i=row_i, col_i=col_i
        ).count()

    def set_following(
        self,
        follower_id: str,
        followed_id: str,
        discreetly: typing.Optional[bool] = None,
        commit: bool = True,
    ) -> None:
        try:
            follow = (
                self._kernel.server_db_session.query(FollowCharacterDocument)
                .filter(
                    FollowCharacterDocument.follower_id == follower_id,
                    FollowCharacterDocument.followed_id == followed_id,
                )
                .one()
            )
        except NoResultFound:
            follow = FollowCharacterDocument(
                follower_id=follower_id, followed_id=followed_id, discreetly=discreetly
            )

        self._kernel.server_db_session.add(follow)

        if commit:
            self._kernel.server_db_session.commit()

    def set_not_following(
        self, follower_id: str, followed_id: str, commit: bool = True
    ) -> None:
        try:
            follow = (
                self._kernel.server_db_session.query(FollowCharacterDocument)
                .filter(
                    FollowCharacterDocument.follower_id == follower_id,
                    FollowCharacterDocument.followed_id == followed_id,
                )
                .one()
            )
        except NoResultFound:
            return

        self._kernel.server_db_session.delete(follow)
        if commit:
            self._kernel.server_db_session.commit()

    def get_zone_character_ids(
        self, row_i: int, col_i: int, alive: typing.Optional[bool] = None
    ) -> typing.List[str]:
        if alive is None:
            query = self._kernel.server_db_session.query(CharacterDocument.id)
        elif alive:
            query = self.alive_query_ids
        else:
            query = self.dead_query_ids

        return [
            r[0]
            for r in query.filter(
                CharacterDocument.world_row_i == row_i,
                CharacterDocument.world_col_i == col_i,
            ).all()
        ]

    def check_can_move_to_zone(
        self, world_row_i: int, world_col_i: int, character: CharacterModel
    ) -> None:
        zone_type = self._kernel.world_map_source.geography.rows[world_row_i][
            world_col_i
        ]
        zone_properties = self._kernel.game.world_manager.get_zone_properties(zone_type)

        # TODO BS 20200707: currently hardcoded
        if (
            zone_properties.require_transport_type
            and TransportType.WALKING not in zone_properties.require_transport_type
        ):
            raise CannotMoveToZoneError("Mode de transport inadapté")

    def get_knowledge_progress(self, character_id: str, knowledge_id: str) -> int:
        try:
            return (
                self._kernel.server_db_session.query(
                    CharacterKnowledgeDocument.progress
                )
                .filter(
                    CharacterKnowledgeDocument.character_id == character_id,
                    CharacterKnowledgeDocument.knowledge_id == knowledge_id,
                )
                .one()[0]
            )
        except NoResultFound:
            return 0

    def increase_knowledge_progress(
        self, character_id: str, knowledge_id: str, ap: int, commit: bool = True
    ) -> bool:
        try:
            knowledge = (
                self._kernel.server_db_session.query(CharacterKnowledgeDocument)
                .filter(
                    CharacterKnowledgeDocument.character_id == character_id,
                    CharacterKnowledgeDocument.knowledge_id == knowledge_id,
                )
                .one()
            )
        except NoResultFound:
            knowledge = CharacterKnowledgeDocument(
                character_id=character_id, knowledge_id=knowledge_id, progress=0
            )

        knowledge_description = self._kernel.game.config.knowledge[knowledge_id]
        knowledge.progress = knowledge.progress + ap

        if knowledge.progress >= knowledge_description.ap_required:
            knowledge.acquired = True

        self._kernel.server_db_session.add(knowledge)
        if commit:
            self._kernel.server_db_session.commit()

        return knowledge.acquired

    def get_pending_actions_count(self, character_id: str) -> int:
        return (
            self._kernel.server_db_session.query(AuthorizePendingActionDocument)
            .filter(
                AuthorizePendingActionDocument.authorized_character_id == character_id
            )
            .count()
        )

    def get_pending_actions(
        self, character_id: str
    ) -> typing.List[PendingActionDocument]:
        pending_action_ids = [
            r[0]
            for r in self._kernel.server_db_session.query(
                AuthorizePendingActionDocument.pending_action_id
            )
            .filter(
                AuthorizePendingActionDocument.authorized_character_id == character_id
            )
            .all()
        ]
        return (
            self._kernel.server_db_session.query(PendingActionDocument)
            .filter(PendingActionDocument.id.in_(pending_action_ids))
            .all()
        )

    def get_pending_action(
        self, pending_action_id: int, check_authorized_character_id: str
    ) -> PendingActionDocument:
        if (
            not self._kernel.server_db_session.query(AuthorizePendingActionDocument)
            .filter(
                AuthorizePendingActionDocument.authorized_character_id
                == check_authorized_character_id,
                AuthorizePendingActionDocument.pending_action_id == pending_action_id,
            )
            .count()
        ):
            raise ImpossibleAction("Action non authorisé")

        return (
            self._kernel.server_db_session.query(PendingActionDocument)
            .filter(PendingActionDocument.id == pending_action_id)
            .one()
        )

    def get_eatables(
        self,
        character: CharacterModel,
        exclude_resource_ids: typing.Optional[typing.List[str]] = None,
    ) -> typing.Generator[
        typing.Tuple[CarriedResourceDescriptionModel, ActionDescriptionModel],
        None,
        None,
    ]:
        exclude_resource_ids = exclude_resource_ids or []
        # With inventory resources
        for carried_resource in self._kernel.resource_lib.get_carried_by(character.id):
            resource_properties = self._kernel.game.config.resources[
                carried_resource.id
            ]

            if resource_properties.id in exclude_resource_ids:
                continue

            for description in resource_properties.descriptions:
                if (
                    description.action_type == ActionType.EAT_RESOURCE
                    and resource_properties.id
                    in [
                        rd.id
                        for rd in description.properties.get("accept_resources", [])
                    ]
                ):
                    yield carried_resource, description

    def get_with_fighters_count(self, character_id: str) -> int:
        here_ids = []
        character_document = self.get_document(character_id)

        for affinity in self._kernel.affinity_lib.get_accepted_affinities(character_id):
            here_ids.extend(
                self._kernel.affinity_lib.get_members_ids(
                    affinity.affinity_id,
                    fighter=True,
                    world_row_i=character_document.world_row_i,
                    world_col_i=character_document.world_col_i,
                    exclude_character_ids=[character_id],
                )
            )

        return len(set(here_ids))

    def get_thirst_sentence(self, percent: float) -> str:
        if percent >= self._kernel.game.config.start_thirst_life_point_loss:
            return "Complètement désydraté !"
        if percent >= 70.0:
            return "Extrêment soif !"
        if percent >= 50.0:
            return "Assoiffé!"
        if percent >= 30.0:
            return "Un peu soif"
        return "Ok"

    def get_hunger_sentence(self, percent: float) -> str:
        if percent >= self._kernel.game.config.start_hunger_life_point_loss:
            return "Complètement affamé !"
        if percent >= 70.0:
            return "Affamé !"
        if percent >= 50.0:
            return "Très faim"
        if percent >= 30.0:
            return "Faim"
        return "Ok"

    def is_there_character_here(
        self,
        world_row_i: int,
        world_col_i: int,
        zone_row_i: int,
        zone_col_i: int,
        alive: bool,
    ) -> bool:
        return bool(
            self.dont_care_alive_query.filter(
                and_(
                    CharacterDocument.alive == alive,
                    CharacterDocument.world_row_i == world_row_i,
                    CharacterDocument.world_col_i == world_col_i,
                    CharacterDocument.zone_row_i == zone_row_i,
                    CharacterDocument.zone_col_i == zone_col_i,
                )
            ).count()
        )

    def setup_avatar_from_pool(self, character_id: str, avatar_index: int) -> None:
        character_doc = self.get_document(character_id)
        avatar_uuid = uuid.uuid4().hex
        avatar_source = self._kernel.avatars_paths[avatar_index]
        util.ensure_avatar_medias(
            self._kernel,
            image_source=avatar_source,
            avatar_uuid=avatar_uuid,
        )
        character_doc.avatar_uuid = avatar_uuid
        character_doc.avatar_is_validated = True
        self._kernel.server_db_session.add(character_doc)
        self._kernel.server_db_session.commit()

    async def refresh_character(self, character_doc: CharacterDocument) -> None:
        await self._kernel.server_zone_events_manager.send_to_sockets(
            WebSocketEvent(
                type=ZoneEventType.NEW_RESUME_TEXT,
                world_row_i=character_doc.world_row_i,
                world_col_i=character_doc.world_col_i,
                data=NewResumeTextData(
                    resume=ListOfItemModel(
                        self._kernel.character_lib.get_resume_text(character_doc.id)
                    )
                ),
            ),
            world_row_i=character_doc.world_row_i,
            world_col_i=character_doc.world_col_i,
            character_ids=[character_doc.id],
        )

    def get_skill_bonus(
        self, character: CharacterModel, skills_ids: typing.List[str]
    ) -> typing.Optional[Bonus]:
        bonuses: typing.List[Bonus] = []
        for skill_id in skills_ids:
            skill = character.skills[skill_id]
            if skill.as_ap_bonus() < 1.0:
                bonuses.append(Bonus(from_skill=skill, coefficient=skill.as_ap_bonus()))

        # Keep only one (the best) bonus
        if bonuses:
            return list(sorted(bonuses, key=lambda b: b.coefficient))[0]

        return None

    def get_stuff_bonus(
        self, character_id: str, qualifiers: typing.List[str]
    ) -> typing.Optional[Bonus]:
        bonuses: typing.List[Bonus] = []
        for stuff in self._kernel.stuff_lib.get_carried_by(
            character_id,
            exclude_crafting=True,
        ):
            stuff_properties = (
                self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                    stuff.stuff_id
                )
            )
            if not stuff_properties.bonuses:
                continue

            bonus_value: typing.Optional[float] = None
            qualified: typing.Any = stuff_properties.bonuses
            for qualifier in qualifiers:
                if qualified := qualified.get(qualifier):
                    if type(qualified) == float:
                        bonus_value = qualified
                        break

            if bonus_value is not None:
                bonuses.append(Bonus(from_stuff=stuff, coefficient=bonus_value))

        # Keep only one (the best) bonus
        if bonuses:
            return list(sorted(bonuses, key=lambda b: b.coefficient))[0]

        return None

    def get_world_coordinates(self, character_id: str) -> typing.Tuple[int, int]:
        return (
            self._kernel.server_db_session.query(
                CharacterDocument.world_row_i, CharacterDocument.world_col_i
            )
            .filter(CharacterDocument.id == character_id)
            .one()
        )

    def get_name(self, character_id: str) -> str:
        return (
            self._kernel.server_db_session.query(CharacterDocument.name)
            .filter(CharacterDocument.id == character_id)
            .one()
        )[0]

    def name_available(self, name: str) -> bool:
        name_to_test = slugify.slugify(name)
        names = [
            row[0]
            for row in self._kernel.server_db_session.query(
                CharacterDocument.name
            ).all()
        ]
        # Must use slug name to ensure no conflict with external tools like Tracim
        for name_ in names:
            if slugify.slugify(name_) == name_to_test:
                return False
        return True

    def character_home_space_name(
        self, character: typing.Union[CharacterDocument, CharacterModel]
    ) -> str:
        return f"🏠 Journal personnel de {character.name}"
