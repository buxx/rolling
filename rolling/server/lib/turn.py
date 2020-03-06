# coding: utf-8
from logging import Logger
import random
import typing

from rolling.exception import ServerTurnError
from rolling.kernel import Kernel
from rolling.log import server_logger
from rolling.map.type.zone import Nothing
from rolling.model.stuff import ZoneGenerationStuff
from rolling.server.document.stuff import StuffDocument
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.types import TurnMode
from rolling.util import character_can_drink_in_its_zone
from rolling.util import get_character_stuff_filled_with_water
from rolling.util import get_stuffs_eatable
from rolling.util import get_stuffs_filled_with_resource_id
from rolling.util import is_there_resource_id_in_zone


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
        # For now, only manager DAY turn mode
        turn_mode = self._kernel.game.config.turn_mode
        if not turn_mode == TurnMode.DAY:
            raise ServerTurnError(f"Turn mode '{turn_mode}' not yet implemented")

        self._generate_stuff()
        self._provide_for_natural_needs()
        self._increment_age()
        self._kill()
        self._reset_action_points()
        self._universe_turn()

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
            if not character_document.is_alive:
                continue

            self._logger.info(f"Provide natural needs of {character_document.name}")

            zone_contains_fresh_water = character_can_drink_in_its_zone(
                self._kernel, character_document
            )
            stuff_with_fresh_water = get_character_stuff_filled_with_water(
                self._kernel, character_id
            )

            # Need drink
            if character_document.feel_thirsty or character_document.dehydrated:
                # Fresh water in zone
                if zone_contains_fresh_water:
                    self._logger.info(
                        f"{character_document.name} need to drink: fresh water in zone"
                    )
                    character_document.dehydrated = False
                # Fresh water in carried stuff
                elif stuff_with_fresh_water is not None:
                    self._logger.info(
                        f"{character_document.name} need to drink: fresh water in stuff {stuff_with_fresh_water.id}"
                    )
                    stuff_doc = self._stuff_lib.get_stuff_doc(stuff_with_fresh_water.id)
                    stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                        stuff_doc.stuff_id
                    )
                    stuff_doc.empty(stuff_properties)
                    character_document.dehydrated = False

            # Dehydrated !
            if character_document.dehydrated:
                character_document.life_points -= 1
                self._kernel.character_lib.add_event(
                    character_id, f"{character_document.name} est déshydraté !"
                )
                self._logger.info(
                    f"{character_document.name} need to drink but no water ! let {character_document.life_points} life points"
                )
            # Only thirsty
            elif character_document.feel_thirsty:
                self._logger.info(
                    f"{character_document.name} need to drink but no water, now dehydrated"
                )
                character_document.dehydrated = True

            # Need drink
            if character_document.feel_hungry or character_document.starved:
                stuff_eatable = None
                try:
                    stuff_eatable = next(get_stuffs_eatable(self._kernel, character_id))
                except StopIteration:
                    pass

                if stuff_eatable:
                    character_document.starved = False
                    self._kernel.stuff_lib.destroy(stuff_eatable.id, commit=False)
                elif character_document.starved:
                    character_document.life_points -= 1
                    self._kernel.character_lib.add_event(
                        character_id, f"{character_document.name} est affamé !"
                    )
                    self._logger.info(
                        f"{character_document.name} need to eat but no eatable ! "
                        f"let {character_document.life_points} life points"
                    )
                else:
                    self._logger.info(
                        f"{character_document.name} need to eat but no eatable stuff, now starved"
                    )
                    character_document.starved = True

            character_document.feel_thirsty = True  # Always need to drink after turn
            character_document.feel_hungry = True  # Always need to eat after turn
            self._character_lib.update(character_document)

    def _increment_age(self) -> None:
        # In future, increment role play age
        character_count = self._character_lib.get_all_character_count()
        self._logger.info(f"Compute age of {character_count} characters")

        for character_id in self._character_lib.get_all_character_ids():
            character_document = self._character_lib.get_document(character_id)
            if not character_document.is_alive:
                continue

            self._logger.debug(
                f'Compute age of "{character_document.name}" ({character_document.id})'
            )
            character_document.alive_since += 1
            self._character_lib.update(character_document)

    def _reset_action_points(self) -> None:
        character_ids = list(self._character_lib.get_all_character_ids())
        self._logger.info(f"Reset action points of {len(character_ids)} characters")

        for character_id in character_ids:
            character_doc = self._kernel.character_lib.get_document(character_id)
            character_doc.action_points = 24.0
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

    def _universe_turn(self) -> None:
        self._kernel.universe_lib.add_new_state()
