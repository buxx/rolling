# coding: utf-8
import typing

from rolling.exception import ImpossibleAction

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.action.base import ActionDescriptionModel


def check_common_is_possible(kernel: "Kernel", description: "ActionDescriptionModel", character: "CharacterModel") -> None:
    character_stuff_ids = [s.id for s in kernel.stuff_lib.get_carried_by(character.id)]
    character_skill_ids = []  # TODO BS 2019-09-26: code it
    one_of_required_stuff_found = False
    one_of_required_skill_found = False
    one_of_required_abilities = False

    for required_one_of_stuff_id in description.properties["required_one_of_stuff_ids"]:
        if required_one_of_stuff_id in character_stuff_ids:
            one_of_required_stuff_found = True

    for required_one_of_skill_id in description.properties["required_one_of_skill_ids"]:
        if required_one_of_skill_id in character_skill_ids:
            one_of_required_skill_found = True

    if kernel.character_lib.have_from_of_abilities(
        character, abilities=description.properties["required_one_of_ability_ids"]
    ):
        one_of_required_abilities = True

    if (
        description.properties["required_one_of_stuff_ids"]
        and not one_of_required_stuff_found
    ):
        raise ImpossibleAction("Manque de matériel")

    if (
        description.properties["required_one_of_skill_ids"]
        and not one_of_required_skill_found
    ):
        raise ImpossibleAction("Manque d'expérience")

    if (
        description.properties["required_one_of_ability_ids"]
        and not one_of_required_abilities
    ):
        raise ImpossibleAction("Manque de matériels ou de compétences")

    for required_all_stuff_id in description.properties["required_all_stuff_ids"]:
        if required_all_stuff_id not in character_stuff_ids:
            raise ImpossibleAction("Manque de matériels")

    for required_all_skill_id in description.properties["required_all_skill_ids"]:
        if required_all_skill_id not in character_skill_ids:
            raise ImpossibleAction("Manque de compétences")
