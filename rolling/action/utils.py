# coding: utf-8
import enum
import typing

from rolling.exception import ConfigurationError
from rolling.exception import ImpossibleAction
from rolling.exception import UnknownStuffError

if typing.TYPE_CHECKING:
    from rolling.action.base import ActionDescriptionModel
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.model.mix import ResourceMixDescription


# TODO BS 20210706: All properties are not covered
def check_common_is_possible(
    kernel: "Kernel",
    description: typing.Union["ActionDescriptionModel", "ResourceMixDescription"],
    character: "CharacterModel",
) -> None:
    character_stuff_ids = [s.stuff_id for s in kernel.stuff_lib.get_carried_by(character.id)]
    error_messages: typing.List[str] = []

    # One or more stuff are required
    if description.properties["required_one_of_stuff_ids"]:
        if not all(
            [
                required_one_of_stuff_id in character_stuff_ids
                for required_one_of_stuff_id in description.properties["required_one_of_stuff_ids"]
            ]
        ):
            error_messages.append("Il vous faut au moins un des objets suivants :")
            for required_one_of_stuff_id in description.properties["required_one_of_stuff_ids"]:
                stuff_description = kernel.game.stuff_manager.get_stuff_properties_by_id(required_one_of_stuff_id)
                error_messages.append(f" - {stuff_description.name}")

    # One or more ability is required
    if description.properties["required_one_of_abilities"]:
        abilities_from_requirement = kernel.character_lib.have_from_of_abilities(
            character, abilities=description.properties["required_one_of_abilities"]
        )
        if not abilities_from_requirement:
            error_messages.append("Il vous faut au moins une des habilités suivantes :")
            for ability in description.properties["required_one_of_abilities"]:
                error_messages.append(f" - {ability.name}")

    # All abilities
    if description.properties["required_all_abilities"]:
        abilities_from_requirement = kernel.character_lib.have_from_of_abilities(
            character, abilities=description.properties["required_all_abilities"]
        )
        if len(abilities_from_requirement) != len(description.properties["required_all_abilities"]):
            error_messages.append("Il vous faut toute les habilités suivantes :")
            for ability in description.properties["required_all_abilities"]:
                error_messages.append(f" - {ability.name}")

    if error_messages:
        raise ImpossibleAction("\n".join(error_messages))


def fill_base_action_properties(
    action_class: type, game_config: "GameConfig", properties: dict, raw_config: dict
) -> dict:
    if "required_one_of_stuff_ids" not in raw_config:
        raise ConfigurationError(f"Cannot find required_one_of_stuff_ids for '{action_class}'")
    if "required_all_stuff_ids" not in raw_config:
        raise ConfigurationError(f"Cannot find required_all_stuff_ids for '{action_class}'")
    if "required_one_of_skill_ids" not in raw_config:
        raise ConfigurationError(f"Cannot find required_one_of_skill_ids for '{action_class}'")
    if "required_all_skill_ids" not in raw_config:
        raise ConfigurationError(f"Cannot find required_all_skill_ids for '{action_class}'")
    if "required_one_of_ability_ids" not in raw_config:
        raise ConfigurationError(f"Cannot find required_one_of_ability_ids for '{action_class}'")
    if "required_all_ability_ids" not in raw_config:
        raise ConfigurationError(f"Cannot find required_all_ability_ids for '{action_class}'")

    properties["required_one_of_stuff_ids"] = []
    for stuff_id in raw_config["required_one_of_stuff_ids"]:
        try:
            # FIXME BS 20200223: use stuff manager (but created after action in stuff manager ...)
            properties["required_one_of_stuff_ids"].append(stuff_id)
        except UnknownStuffError:
            raise ConfigurationError(f"stuff_id unknown for '{action_class}'")

    properties["required_all_stuff_ids"] = []
    for stuff_id in raw_config["required_all_stuff_ids"]:
        try:
            # FIXME BS 20200223: use stuff manager (but created after action in stuff manager ...)
            properties["required_all_stuff_ids"].append(stuff_id)
        except UnknownStuffError:
            raise ConfigurationError(f"stuff_id unknown for '{action_class}'")

    properties["required_one_of_skills"] = []
    for skill_id in raw_config["required_one_of_skill_ids"]:
        pass  # TODO: implement

    properties["required_all_skills"] = []
    for skill_id in raw_config["required_all_skill_ids"]:
        pass  # TODO: implement

    properties["required_one_of_abilities"] = []
    for ability_id in raw_config["required_one_of_ability_ids"]:
        try:
            properties["required_one_of_abilities"].append(game_config.abilities[ability_id])
        except KeyError:
            raise ConfigurationError(f"ability_id '{ability_id}' is unknown for '{action_class}'")

    properties["required_all_abilities"] = []
    for ability_id in raw_config["required_all_ability_ids"]:
        try:
            properties["required_all_abilities"].append(game_config.abilities[ability_id])
        except KeyError:
            raise ConfigurationError(f"ability_id '{ability_id}' is unknown for '{action_class}'")

    return properties


class AroundPercent(enum.Enum):
    LESS = "LESS"
    IN = "IN"
    MORE = "MORE"


def in_percent(reference: float, number: float, percent: int) -> AroundPercent:
    percent_val = reference * (percent / 100)
    minimum = reference - percent_val
    maximum = reference + percent_val

    if number < minimum:
        return AroundPercent.LESS

    if number > maximum:
        return AroundPercent.MORE

    return AroundPercent.IN
