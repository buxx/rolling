# coding: utf-8
import click

from rolling.server.base import get_kernel
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
    kernel.resource_lib.add_resource_to_character(
        character_.id, resource_id, quantity=quantity
    )


if __name__ == "__main__":
    main()
