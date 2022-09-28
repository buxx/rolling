# coding: utf-8
import asyncio
import click
from random import choice
import requests
from sqlalchemy.exc import NoResultFound
import typing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from rolling.map.source import ZoneMap
from rolling.map.type.world import WorldMapTileType
from rolling.model.zone import ZoneMapTileProduction
from rolling.server.application import HEADER_NAME__DISABLE_AUTH_TOKEN
from rolling.server.base import get_kernel
from rolling.server.document.corpse import AnimatedCorpseDocument
from rolling.server.document.corpse import AnimatedCorpseType
from rolling.server.document.skill import CharacterSkillDocument
from rolling.server.lib.character import CharacterLib
from rolling.server.lib.stuff import StuffLib


@click.group()
def main():
    pass


@main.group()
def character():
    pass


@character.group()
def stuff():
    pass


@character.group()
def resource():
    pass


@character.group()
def knowledge():
    pass


@stuff.command()
@click.argument("game-config-dir")
@click.argument("character-name")
@click.argument("stuff-id")
def create(game_config_dir: str, character_name: str, stuff_id: str) -> None:
    click.echo("Preparing libs ...")
    kernel = get_kernel(game_config_folder=game_config_dir)
    stuff_lib = StuffLib(kernel)
    character_lib = CharacterLib(kernel)

    click.echo("Preparing libs ... OK")
    click.echo("Search character by name")
    character_ = character_lib.get_by_name(character_name)

    click.echo("Create stuff")
    stuff_properties = kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
    stuff_doc = stuff_lib.create_document_from_stuff_properties(stuff_properties)
    stuff_doc.carried_by_id = character_.id
    click.echo("Commit changes")
    kernel.server_db_session.add(stuff_doc)
    kernel.server_db_session.commit()


@resource.command()
@click.argument("game-config-dir")
@click.argument("character-name")
@click.argument("resource-id")
@click.argument("quantity", type=float)
def create(
    game_config_dir: str, character_name: str, resource_id: str, quantity: float
) -> None:
    click.echo("Preparing kernel")
    kernel = get_kernel(game_config_folder=game_config_dir)
    click.echo("Search character by name")
    character_ = kernel.character_lib.get_by_name(character_name)

    click.echo("Add resource")
    kernel.resource_lib.add_resource_to(
        character_id=character_.id, resource_id=resource_id, quantity=quantity
    )


@character.command()
@click.argument("game-config-dir")
@click.argument("character-name")
@click.argument("world_row_i", type=int)
@click.argument("world_col_i", type=int)
def move(
    game_config_dir: str, character_name: str, world_row_i: int, world_col_i: int
) -> None:
    click.echo("Preparing kernel")
    kernel = get_kernel(game_config_folder=game_config_dir)
    click.echo("Search character by name")
    character_ = kernel.character_lib.get_by_name(character_name)

    click.echo("Move")
    asyncio.run(kernel.character_lib.move(character_, world_row_i, world_col_i))


@character.command()
@click.argument("game-config-dir")
@click.argument("character-name")
@click.argument("action_points", type=int)
def ap(game_config_dir: str, character_name: str, action_points: int) -> None:
    click.echo("Preparing kernel")
    kernel = get_kernel(game_config_folder=game_config_dir)
    click.echo("Search character by name")
    character_ = kernel.character_lib.get_by_name(character_name)
    character_doc = kernel.character_lib.get_document(character_.id)
    click.echo("Set ap")
    character_doc.action_points = action_points
    kernel.server_db_session.add(character_doc)
    kernel.server_db_session.commit()


@knowledge.command()
@click.argument("game-config-dir")
@click.argument("character-name")
@click.argument("knowledge-id")
def setup(game_config_dir: str, character_name: str, knowledge_id: str) -> None:
    click.echo("Preparing kernel")
    kernel = get_kernel(game_config_folder=game_config_dir)
    click.echo("Search character by name")
    character_ = kernel.character_lib.get_by_name(character_name)
    character_doc = kernel.character_lib.get_document(character_.id)
    click.echo("Setup knowledge")
    kernel.character_lib.increase_knowledge_progress(
        character_doc.id,
        knowledge_id,
        ap=int(kernel.game.config.knowledge[knowledge_id].ap_required),
    )


@main.command()
@click.argument("game-config-dir")
@click.argument("world-map-source")
@click.argument("zone-map-folder")
def sync_zone_resources(
    game_config_dir: str, world_map_source: str, zone_map_folder: str
) -> None:
    click.echo("Preparing kernel ...")
    main_kernel = get_kernel(
        game_config_folder=game_config_dir,
        world_map_source_path=world_map_source,
        tile_maps_folder_path=zone_map_folder,
    )

    def _work(coordinates: typing.Tuple[int, int]):
        world_row_i, world_col_i = coordinates
        click.echo(f"Process {world_row_i}.{world_col_i} ...")

        zone_map: ZoneMap = main_kernel.tile_maps_by_position[
            (world_row_i, world_col_i)
        ]
        # Use dedicated process to ensure db session is not shared
        process_kernel = get_kernel(
            game_config_folder=game_config_dir,
            world_map_source_path=world_map_source,
            tile_maps_folder_path=zone_map_folder,
        )
        for zone_row_i, zone_row in enumerate(zone_map.source.geography.rows):
            for zone_col_i, tile_type in enumerate(zone_row):
                tiles_properties = main_kernel.game.world_manager.world.tiles_properties
                try:
                    tile_properties = tiles_properties[tile_type]
                except KeyError:
                    continue

                production: ZoneMapTileProduction
                for production in tile_properties.produce:
                    if production.infinite:
                        continue
                    try:
                        _ = process_kernel.zone_lib.get_zone_ressource_doc(
                            world_row_i=world_row_i,
                            world_col_i=world_col_i,
                            zone_row_i=zone_row_i,
                            zone_col_i=zone_col_i,
                            resource_id=production.resource.id,
                        )
                    except NoResultFound:
                        _ = process_kernel.zone_lib.create_zone_ressource_doc(
                            world_row_i=world_row_i,
                            world_col_i=world_col_i,
                            zone_row_i=zone_row_i,
                            zone_col_i=zone_col_i,
                            resource_id=production.resource.id,
                            quantity=production.start_capacity,
                            destroy_when_empty=production.destroy_when_empty,
                            replace_by_when_destroyed=production.replace_by_when_destroyed,
                        )

    coordinates = []
    for world_row_i, world_row in enumerate(
        main_kernel.world_map_source.geography.rows
    ):
        for world_col_i, _ in enumerate(world_row):
            coordinates.append((world_row_i, world_col_i))

    click.echo("Start execution ...")
    with ThreadPoolExecutor(max_workers=16) as executor:
        executor.map(_work, coordinates)

    click.echo("Finished ...")


@main.command()
@click.argument("game-config-dir")
@click.argument("world-map-source")
@click.argument("zone-map-folder")
@click.argument("zone_type")
@click.argument("ac_type")
@click.argument("count", type=int)
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=5000, type=int)
@click.option("--disable-sync", is_flag=True)
def populate_ac(
    game_config_dir: str,
    world_map_source: str,
    zone_map_folder: str,
    zone_type: str,
    ac_type: str,
    count: int,
    host: str,
    port: int,
    disable_sync: bool,
) -> None:
    click.echo("Preparing kernel")
    animated_corpse_type = AnimatedCorpseType(ac_type)
    filter_zone_type = WorldMapTileType.get_for_id(zone_type)
    kernel = get_kernel(
        game_config_folder=game_config_dir,
        world_map_source_path=world_map_source,
        tile_maps_folder_path=zone_map_folder,
    )
    universe_state = kernel.universe_lib.get_last_state()

    zone_type: typing.Type[WorldMapTileType]
    for world_row_i, world_row in enumerate(kernel.world_map_source.geography.rows):
        for world_col_i, zone_type in enumerate(world_row):
            if zone_type != filter_zone_type:
                click.echo(f"Ignore {world_row_i}.{world_col_i} ({zone_type.__name__})")
                continue
            click.echo(
                f"Process {world_row_i}.{world_col_i} ({zone_type.__name__}) ..."
            )

            animated_corpses = kernel.animated_corpse_lib.get_all(
                world_row_i=world_row_i,
                world_col_i=world_col_i,
                type_=animated_corpse_type,
            )

            if len(animated_corpses) >= count:
                click.echo(f"{len(animated_corpses)} found, do nothing")
                continue

            for _ in range(count - len(animated_corpses)):
                click.echo(f"Create new animated corpse ...")

                traversable_coordinates = kernel.get_traversable_coordinates(
                    world_row_i, world_col_i
                )
                if not traversable_coordinates:
                    click.echo(f"ERROR: no traversable coordinate found !")
                    continue
                zone_row_i, zone_col_i = choice(traversable_coordinates)

                animated_corpse = kernel.animated_corpse_lib.create(
                    AnimatedCorpseDocument(
                        alive_since=universe_state.turn,
                        world_row_i=world_row_i,
                        world_col_i=world_col_i,
                        zone_row_i=zone_row_i,
                        zone_col_i=zone_col_i,
                        alive=True,
                        type_=animated_corpse_type.value,
                    )
                )

                if disable_sync:
                    click.echo(f"Sync is disabled, not not sync")
                click.echo(f"Sync newly added animated corpse (on {host}:{port})")

                response = requests.put(
                    url=f"http://{host}:{port}/ac-signal/new/{animated_corpse.id}",
                    headers={
                        HEADER_NAME__DISABLE_AUTH_TOKEN: kernel.server_config.disable_auth_token
                    },
                )
                if response.status_code != 204:
                    click.echo(
                        f"ERROR: Signal newly added result error : code {response.status_code}"
                    )


@main.command()
@click.argument("game-config-dir")
@click.argument("world-map-source")
@click.argument("zone-map-folder")
def sync_build_health(
    game_config_dir: str, world_map_source: str, zone_map_folder: str
) -> None:
    click.echo("Preparing kernel")
    kernel = get_kernel(
        game_config_folder=game_config_dir,
        world_map_source_path=world_map_source,
        tile_maps_folder_path=zone_map_folder,
    )

    for build_id in kernel.build_lib.get_all_ids(is_on=None):
        build_doc = kernel.build_lib.get_build_doc(build_id)
        build_description = kernel.game.config.builds[build_doc.build_id]
        if build_description.robustness is not None and build_doc.health is None:
            click.echo(f"Fixing build {build_doc.id}")
            build_doc.health = build_description.robustness
            kernel.server_db_session.add(build_doc)
            kernel.server_db_session.commit()


@main.command()
@click.argument("game-config-dir")
@click.argument("world-map-source")
@click.argument("zone-map-folder")
def sync_character_skill(
    game_config_dir: str, world_map_source: str, zone_map_folder: str
) -> None:
    click.echo("Preparing kernel")
    kernel = get_kernel(
        game_config_folder=game_config_dir,
        world_map_source_path=world_map_source,
        tile_maps_folder_path=zone_map_folder,
    )

    available_skills = list(kernel.game.config.skills.keys())
    for skill_doc in (
        kernel.server_db_session.query(CharacterSkillDocument)
        .filter(CharacterSkillDocument.skill_id.not_in(available_skills))
        .all()
    ):
        click.echo(f"Delete {skill_doc.character_id} {skill_doc.skill_id}")
        kernel.server_db_session.delete(skill_doc)
        kernel.server_db_session.commit()


@main.command()
@click.argument("game-config-dir")
@click.argument("world-map-source")
@click.argument("zone-map-folder")
def sync_drop_resource_nowhere(
    game_config_dir: str, world_map_source: str, zone_map_folder: str
) -> None:
    click.echo("Preparing kernel")
    kernel = get_kernel(
        game_config_folder=game_config_dir,
        world_map_source_path=world_map_source,
        tile_maps_folder_path=zone_map_folder,
    )

    for resource_description in kernel.game.config.resources.values():
        if resource_description.drop_to_nowhere:
            for resource_doc in kernel.resource_lib.get_base_query(
                resource_id=resource_description.id,
            ):
                kernel.server_db_session.delete(resource_doc)
                kernel.server_db_session.commit()


if __name__ == "__main__":
    main()
