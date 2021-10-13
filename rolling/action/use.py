import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import ImpossibleAction
from rolling.exception import WrongInputError
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.util import EmptyModel

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


class NotUseAsBagAction(WithStuffAction):
    exclude_from_actions_page = True
    input_model: typing.Type[object] = EmptyModel
    input_model_serializer: serpyco.Serializer

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        bag_ids = [bag.id for bag in character.bags]
        if stuff.id not in bag_ids:
            raise ImpossibleAction("Vous n'utilisez pas ce sac")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> None:
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Ne plus utiliser {stuff.name} comme sac",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.NOT_USE_AS_BAG,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> Description:
        self._kernel.stuff_lib.unset_as_used_as_bag(character.id, stuff.id)
        return Description(title="Action effectué")


class UseAsBagAction(WithStuffAction):
    exclude_from_actions_page = True
    input_model: typing.Type[object] = EmptyModel
    input_model_serializer: serpyco.Serializer

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        # TODO BS 2019-09-03: permit multiple bags ?
        if not stuff.ready_for_use:
            raise ImpossibleAction(f"{stuff.name} n'est pas utilisable")
        if character.bags:
            raise ImpossibleAction("Vous utilisez déjà un sac")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> None:
        # TODO BS 2019-09-03: check stuff owned
        if character.bags:
            raise WrongInputError("Vous utilisez déjà un sac")

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Utiliser {stuff.name} comme sac",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.USE_AS_BAG,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> Description:
        self._kernel.stuff_lib.set_as_used_as_bag(character.id, stuff.id)
        return Description(title="Action effectué")


class UseAsWeaponAction(WithStuffAction):
    exclude_from_actions_page = True
    input_model: typing.Type[EmptyModel] = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if not stuff.weapon:
            raise ImpossibleAction("Ce n'est pas une arme")
        if not stuff.ready_for_use:
            raise ImpossibleAction(f"{stuff.name} n'est pas utilisable")
        if character.weapon:
            raise ImpossibleAction("Vous utilisez déjà une arme")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> None:
        # TODO BS 2019-09-03: check stuff owned
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Utiliser {stuff.name} comme arme",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.USE_AS_WEAPON,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> Description:
        self._kernel.stuff_lib.set_as_used_as_weapon(character.id, stuff.id)
        return Description(title="Action effectué")


class NotUseAsWeaponAction(WithStuffAction):
    exclude_from_actions_page = True
    input_model: typing.Type[EmptyModel] = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if character.weapon and character.weapon.id == stuff.id:
            return
        raise ImpossibleAction("Vous n'utilisez pas cette arme")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> None:
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Ne plus utiliser {stuff.name} comme arme",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.NOT_USE_AS_WEAPON,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> Description:
        self._kernel.stuff_lib.unset_as_used_as_weapon(character.id, stuff.id)
        return Description(title="Action effectué")


class UseAsShieldAction(WithStuffAction):
    exclude_from_actions_page = True
    input_model: typing.Type[EmptyModel] = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if not stuff.shield:
            raise ImpossibleAction("Ce n'est pas un bouclier")
        if not stuff.ready_for_use:
            raise ImpossibleAction(f"{stuff.name} n'est pas utilisable")
        if character.shield:
            raise ImpossibleAction("Vous utilisez déjà un bouclier")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> None:
        # TODO BS 2019-09-03: check stuff owned
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Utiliser {stuff.name} comme bouclier",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.USE_AS_SHIELD,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> Description:
        self._kernel.stuff_lib.set_as_used_as_shield(character.id, stuff.id)
        return Description(title="Action effectué")


class NotUseAsShieldAction(WithStuffAction):
    exclude_from_actions_page = True
    input_model: typing.Type[EmptyModel] = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if character.shield and character.shield.id == stuff.id:
            return
        raise ImpossibleAction("Vous n'utilisez pas ce bouclier")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> None:
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Ne plus utiliser {stuff.name} comme bouclier",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.NOT_USE_AS_SHIELD,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> Description:
        self._kernel.stuff_lib.unset_as_used_as_shield(character.id, stuff.id)
        return Description(title="Action effectué")


class UseAsArmorAction(WithStuffAction):
    exclude_from_actions_page = True
    input_model: typing.Type[EmptyModel] = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if not stuff.armor:
            raise ImpossibleAction("Ce n'est pas une armure/protection")
        if not stuff.ready_for_use:
            raise ImpossibleAction(f"{stuff.name} n'est pas utilisable")
        if character.armor:
            raise ImpossibleAction("Vous utilisez déjà une armure/protection")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> None:
        # TODO BS 2019-09-03: check stuff owned
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Utiliser {stuff.name} comme armure/protection",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.USE_AS_ARMOR,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> Description:
        self._kernel.stuff_lib.set_as_used_as_armor(character.id, stuff.id)
        return Description(title="Action effectué")


class NotUseAsArmorAction(WithStuffAction):
    exclude_from_actions_page = True
    input_model: typing.Type[EmptyModel] = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if character.armor and character.armor.id == stuff.id:
            return
        raise ImpossibleAction("Vous n'utilisez pas cette armure/equipement")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> None:
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Ne plus utiliser {stuff.name} comme armure/equipement",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.NOT_USE_AS_ARMOR,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: EmptyModel
    ) -> Description:
        self._kernel.stuff_lib.unset_as_used_as_armor(character.id, stuff.id)
        return Description(title="Action effectué")
