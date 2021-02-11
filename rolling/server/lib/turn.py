# coding: utf-8
from logging import Logger
import random
from sqlalchemy.orm.exc import NoResultFound
import typing

from rolling.action.drink import DrinkStuffAction
from rolling.action.eat import EatResourceAction
from rolling.exception import ErrorWhenConsume
from rolling.exception import NoCarriedResource
from rolling.exception import NotEnoughResource
from rolling.kernel import Kernel
from rolling.log import server_logger
from rolling.map.type.zone import Nothing
from rolling.model.stuff import ZoneGenerationStuff
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.util import character_can_drink_in_its_zone
from rolling.util import get_stuffs_filled_with_resource_id


class TurnLib:
    def __init__(
        self,
        kernel: Kernel,
        character_lib: CharacterLib,
        stuff_lib: StuffLib,
        logger: typing.Optional[Logger] = None,
    ) -> None:
        self._kernel = kernel
        self._character_lib = character_lib
        self._stuff_lib = stuff_lib
        self._logger = logger or server_logger

    def execute_turn(self) -> None:
        # FIXME: update stuff generation for hour ticks
        # self._generate_stuff()
        self._provide_for_natural_needs()
        self._improve_conditions()
        self._increment_age()
        self._kill()
        self._manage_characters_props()
        self._builds_consumptions()
        self._universe_turn()

        # FIXME BS NOW: remove pending actions and authorizations
        self._kernel.server_db_session.commit()

    def _generate_stuff(self) -> None:
        self._logger.info("Generate stuff")
        generation_stuff_by_zone_type = (
            self._kernel.game.world_manager.get_generation_stuff_by_zone_type()
        )
        zone_properties_by_zone_type = (
            self._kernel.game.world_manager.get_zone_properties_by_zone_type()
        )

        for row_i, row in enumerate(self._kernel.world_map_source.geography.rows):
            for col_i, zone_type in enumerate(row):
                if zone_type not in generation_stuff_by_zone_type:
                    self._logger.debug(f"No generation info for {zone_type} at {row_i},{col_i}")
                    continue

                # Choose some stuff
                zone_property = zone_properties_by_zone_type[zone_type]
                generation_stuffs = generation_stuff_by_zone_type[zone_type]
                weights = [s.probability for s in generation_stuffs]

                if not generation_stuffs:
                    continue

                chosen_stuff = random.choices(
                    population=generation_stuffs,
                    weights=weights,
                    k=zone_property.generation_info.count,
                )
                self._logger.debug(
                    f"Start generation of {zone_property.generation_info.count} stuff "
                    f"for {zone_type} at {row_i},{col_i}"
                )

                # TODO BS 2019-06-18: Be able to place stuff near specific tiles types
                # Choose some positions where place stuff
                zone_source_geo = self._kernel.tile_maps_by_position[row_i, col_i].source.geography
                chosen_positions: typing.List[typing.Tuple[int, int]] = []
                for i in range(zone_property.generation_info.count):
                    retry = 0
                    rand_row_i = None
                    rand_col_i = None

                    while retry <= 100:
                        rand_row_i = random.randint(0, zone_source_geo.height - 1)
                        rand_col_i = random.randint(0, zone_source_geo.width - 1)
                        if zone_source_geo.rows[rand_row_i][rand_col_i] != Nothing:
                            break

                    if rand_col_i is not None and rand_row_i is not None:
                        chosen_positions.append((rand_row_i, rand_col_i))
                    else:
                        self._logger.error("Unable to find a place")

                for chosen_position in chosen_positions:
                    stuff_to_place: ZoneGenerationStuff = chosen_stuff.pop()
                    self._logger.info(
                        f"Place {stuff_to_place.stuff.id} at {chosen_position[0]},{chosen_position[1]}"
                    )
                    stuff_doc = self._stuff_lib.create_document_from_generation_properties(
                        stuff_to_place,
                        stuff_id=stuff_to_place.stuff.id,
                        world_col_i=col_i,
                        world_row_i=row_i,
                        zone_col_i=chosen_position[0],
                        zone_row_i=chosen_position[1],
                    )
                    self._stuff_lib.add_stuff(stuff_doc, commit=False)
        self._kernel.server_db_session.commit()

    def _provide_for_natural_needs(self) -> None:
        character_ids = list(self._character_lib.get_all_character_ids())
        self._logger.info(f"Provide natural needs of {len(character_ids)} characters")

        for character_id in character_ids:
            character_document = self._character_lib.get_document(character_id)
            character = self._character_lib.get(character_id)
            if not character_document.is_alive:
                continue

            self._logger.info(
                f"Provide natural needs of {character_document.name} {character_document.id}"
            )
            zone_contains_fresh_water = character_can_drink_in_its_zone(self._kernel, character)

            # DRINKING
            character_document.thirst = min(
                100.0,
                float(character_document.thirst) + self._kernel.game.config.thirst_change_per_tick,
            )
            self._logger.info(f"Increase thirst to {character_document.thirst}")

            drink_in = []
            while character_document.thirst > self._kernel.game.config.stop_auto_drink_thirst:
                stuff_with_fresh_water = None
                try:
                    stuff_with_fresh_water = next(
                        get_stuffs_filled_with_resource_id(
                            self._kernel,
                            character_id,
                            self._kernel.game.config.fresh_water_resource_id,
                            exclude_stuff_ids=[s.id for s in drink_in],
                        )
                    )
                except StopIteration:
                    pass

                have_drink = False
                if zone_contains_fresh_water:
                    self._logger.info(f"Drink in zone")
                    have_drink = True
                    character_document.thirst = self._kernel.game.config.stop_auto_drink_thirst

                elif stuff_with_fresh_water is not None:
                    self._logger.info(f"Drink in stuff {stuff_with_fresh_water.id}")
                    have_drink = True

                    stuff_doc = self._kernel.stuff_lib.get_stuff_doc(stuff_with_fresh_water.id)
                    drink_water_action_description = (
                        self._kernel.game.get_drink_water_action_description()
                    )
                    DrinkStuffAction.drink(
                        self._kernel,
                        character_document,
                        stuff_doc,
                        all_possible=True,
                        consume_per_tick=drink_water_action_description.properties[
                            "consume_per_tick"
                        ],
                    )
                    drink_in.append(stuff_doc)
                    self._logger.info(f"Now thirst to {character_document.thirst}")
                else:
                    self._logger.info(f"No drink")

                if not have_drink:
                    break

            # Dehydrated ! Losing LP
            if (
                float(character_document.thirst)
                >= self._kernel.game.config.start_thirst_life_point_loss
            ):
                character_document.life_points = max(
                    0.0,
                    float(character_document.life_points)
                    - self._kernel.game.config.thirst_life_point_loss_per_tick,
                )
                self._logger.info(
                    f"Losing LP because dehydrated for {character_document.life_points}"
                )

            # EATING
            character_document.hunger = min(
                100.0,
                float(character_document.hunger) + self._kernel.game.config.hunger_change_per_tick,
            )
            self._logger.info(f"Increase hunger to {character_document.hunger}")

            eat_resource_ids = []
            while character_document.hunger > self._kernel.game.config.stop_auto_eat_hunger:
                have_eat = False

                try:
                    carried_resource, action_description = next(
                        self._kernel.character_lib.get_eatables(
                            character, exclude_resource_ids=eat_resource_ids
                        )
                    )
                    have_eat = True
                    try:
                        EatResourceAction.eat(
                            self._kernel,
                            character_doc=character_document,
                            resource_id=carried_resource.id,
                            all_possible=True,
                            consume_per_tick=action_description.properties["consume_per_tick"],
                        )
                    except NoCarriedResource:
                        pass
                    self._logger.info(f"Have eat with {carried_resource.id}")
                    eat_resource_ids.append(carried_resource.id)
                except StopIteration:
                    pass

                if not have_eat:
                    self._logger.info("Have no eat")
                    break

            # Hungry ! Losing LP
            if (
                float(character_document.hunger)
                >= self._kernel.game.config.start_hunger_life_point_loss
            ):
                character_document.life_points = max(
                    0.0,
                    float(character_document.life_points)
                    - self._kernel.game.config.hunger_life_point_loss_per_tick,
                )
                self._logger.info(f"Losing LP because hungry for {character_document.life_points}")

            self._character_lib.update(character_document)

    def _improve_conditions(self) -> None:
        character_ids = list(self._character_lib.get_all_character_ids())
        self._logger.info(f"Improve conditions of {len(character_ids)} characters")

        for character_id in character_ids:
            # TODO: diseases, effect, etc
            character_document = self._character_lib.get_document(character_id)
            if not character_document.is_alive:
                continue

            self._logger.info(
                f"Provide conditions of {character_document.name} {character_document.id}"
            )

            if (
                float(character_document.hunger)
                <= self._kernel.game.config.limit_hunger_increase_life_point
                and float(character_document.thirst)
                <= self._kernel.game.config.limit_thirst_increase_life_point
            ):
                new_tiredness = self._character_lib.reduce_tiredness(
                    character_id, self._kernel.game.config.reduce_tiredness_per_tick
                )
                self._logger.info(f"Reduce tiredness for {new_tiredness}")

            if (
                float(character_document.hunger)
                <= self._kernel.game.config.limit_hunger_reduce_tiredness
                and float(character_document.thirst)
                <= self._kernel.game.config.limit_thirst_reduce_tiredness
            ):
                character_document.life_points = min(
                    character_document.max_life_comp,
                    float(character_document.life_points)
                    + self._kernel.game.config.life_point_points_per_tick,
                )
                self._logger.info(f"Increase life points for {character_document.life_points}")

            self._character_lib.update(character_document)

    def _increment_age(self) -> None:
        # In future, increment role play age
        character_count = self._character_lib.get_all_character_count()
        self._logger.info(f"Compute age of {character_count} characters")

        for character_id in self._character_lib.get_all_character_ids():
            character_document = self._character_lib.get_document(character_id)
            if not character_document.is_alive:
                continue

            self._logger.info(
                f'Compute age of "{character_document.name}" ({character_document.id})'
            )
            character_document.alive_since += 1
            self._logger.info(f"New age: {character_document.alive_since}")
            self._character_lib.update(character_document)

    def _manage_characters_props(self) -> None:
        character_ids = list(self._character_lib.get_all_character_ids())
        self._logger.info(f"Manage props of {len(character_ids)} characters")

        for character_id in character_ids:
            character_doc = self._kernel.character_lib.get_document(character_id)
            if not character_doc.is_alive:
                continue

            self._logger.info(f"Manage props of {character_doc.name} {character_doc.id}")

            character_doc.action_points = min(
                float(character_doc.max_action_points),
                float(character_doc.action_points)
                + self._kernel.game.config.action_points_per_tick,
            )
            server_logger.info(f"New AP: {character_doc.action_points}")
            self._kernel.server_db_session.add(character_doc)

        self._kernel.server_db_session.commit()

    def _kill(self) -> None:
        # In future, increment role play age
        self._logger.info(f"Kill some characters")

        for character_id in self._character_lib.get_all_character_ids():
            character_doc = self._kernel.character_lib.get_document(character_id)
            if character_doc.alive and character_doc.life_points <= 0:
                self._logger.info(
                    f"'{character_doc.name}' have '{character_doc.life_points}' life point. kill it."
                )
                self._kernel.character_lib.kill(character_doc.id)

    def _builds_consumptions(self) -> None:
        self._logger.info("Build consumptions")
        builds = self._kernel.build_lib.get_all(is_on=True)
        self._logger.info(f"Found {len(builds)} builds")
        for build_doc in builds:
            build_description = self._kernel.game.config.builds[build_doc.build_id]
            if build_description.turn_require_resources:
                have_all_resources = True
                for turn_require_resource in build_description.turn_require_resources:
                    try:
                        self._kernel.resource_lib.get_one_stored_in_build(
                            build_doc.id,
                            resource_id=turn_require_resource.resource_id,
                            quantity=turn_require_resource.quantity,
                        )
                    except NoResultFound:
                        have_all_resources = False
                if have_all_resources:
                    for turn_require_resource in build_description.turn_require_resources:
                        self._kernel.resource_lib.reduce_stored_in(
                            build_id=build_doc.id,
                            resource_id=turn_require_resource.resource_id,
                            quantity=turn_require_resource.quantity,
                            commit=False,
                        )
                else:
                    build_doc.is_on = False
            self._kernel.server_db_session.commit()

    def _universe_turn(self) -> None:
        self._kernel.universe_lib.add_new_state()
