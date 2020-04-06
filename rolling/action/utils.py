# coding: utf-8
import enum
import typing

from rolling.exception import ConfigurationError
from rolling.exception import ImpossibleAction
from rolling.exception import UnknownStuffError

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.action.base import ActionDescriptionModel
    from rolling.game.base import GameConfig


def check_common_is_possible(
    kernel: "Kernel", description: "ActionDescriptionModel", character: "CharacterModel"
) -> None:
    character_stuff_ids = [s.stuff_id for s in kernel.stuff_lib.get_carried_by(character.id)]
    character_skill_ids = []  # TODO BS 2019-09-26: code it
    one_of_required_stuff_found = False
    one_of_required_skill_found = False
    one_of_required_abilities = False

    for required_one_of_stuff_id in description.properties["required_one_of_stuff_ids"]:
        if required_one_of_stuff_id in character_stuff_ids:
            one_of_required_stuff_found = True

    for required_one_of_skill in description.properties["required_one_of_skills"]:
        if required_one_of_skill.id in character_skill_ids:
            one_of_required_skill_found = True

    if kernel.character_lib.have_from_of_abilities(
        character, abilities=description.properties["required_one_of_abilities"]
    ):
        one_of_required_abilities = True

    if description.properties["required_one_of_stuff_ids"] and not one_of_required_stuff_found:
        raise ImpossibleAction("Manque de matériel")

    if description.properties["required_one_of_skills"] and not one_of_required_skill_found:
        raise ImpossibleAction("Manque d'expérience")

    if description.properties["required_one_of_abilities"] and not one_of_required_abilities:
        raise ImpossibleAction("Manque de matériels ou de compétences")

    for required_all_stuff_id in description.properties["required_all_stuff_ids"]:
        if required_all_stuff_id not in character_stuff_ids:
            raise ImpossibleAction("Manque de matériels")

    for required_all_skill_id in description.properties["required_all_skills"]:
        if required_all_skill_id not in character_skill_ids:
            raise ImpossibleAction("Manque de compétences")


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
