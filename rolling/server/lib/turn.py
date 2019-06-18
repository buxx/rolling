# coding: utf-8
import logging
from logging import Logger
import random
import typing

from rolling.kernel import Kernel
from rolling.log import server_logger
from rolling.map.type.zone import Nothing
from rolling.model.stuff import ZoneGenerationStuff
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib


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

    def _increment_age(self) -> None:
        # In future, increment role play age
        character_count = self._character_lib.get_all_character_count()
        self._logger.info(f"Compute age of {character_count} characters")

        for character_id in self._character_lib.get_all_character_ids():
            character_document = self._character_lib.get_document(character_id)
            self._logger.debug(
                f'Compute age of "{character_document.name}" ({character_document.id})'
            )
            character_document.alive_since += 1
            self._character_lib.update(character_document)
