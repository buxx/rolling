# coding: utf-8
import logging
from logging import Logger
import random
import typing

from rolling.kernel import Kernel
from rolling.log import server_logger
from rolling.map.type.zone import Nothing
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.resource import ResourceType
from rolling.model.stuff import ZoneGenerationStuff
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib
from rolling.util import get_stuffs_filled_with_resource_type
from rolling.util import is_there_resource_type_in_zone


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
        self._generate_stuff()
        self._provide_for_natural_needs()
        self._increment_age()

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
                    self._logger.debug(
                        f"No generation info for {zone_type} at {row_i},{col_i}"
                    )
                    continue

                # Choose some stuff
                zone_property = zone_properties_by_zone_type[zone_type]
                generation_stuffs = generation_stuff_by_zone_type[zone_type]
                weights = [s.probability for s in generation_stuffs]
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
                zone_source_geo = self._kernel.tile_maps_by_position[
                    row_i, col_i
                ].source.geography
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

            # FIXME BS 2019-07-09: if resource with fresh water accessible (find path)
            #  (and thirsty): drink
            zone_source = self._kernel.tile_maps_by_position[
                (character_document.world_row_i, character_document.world_col_i)
            ].source
            zone_contains_fresh_water = is_there_resource_type_in_zone(
                ResourceType.FRESH_WATER, zone_source
            )
            stuff_with_fresh_water = None
            try:
                stuff_with_fresh_water = next(
                    get_stuffs_filled_with_resource_type(
                        self._kernel, character_id, ResourceType.FRESH_WATER
                    )
                )
            except StopIteration:
                pass

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
                        f"{character_document.name} need to drink: fresh water in stuff {stuff_doc.id}"
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
                self._logger.info(
                    f"{character_document.name} need to drink but no water ! let {character_document.life_points} life points"
                )
            # Only thirsty
            elif character_document.feel_thirsty:
                self._logger.info(
                    f"{character_document.name} need to drink but no water, now dehydrated"
                )
                character_document.dehydrated = True

            character_document.feel_thirsty = True  # Always need to drink after turn
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