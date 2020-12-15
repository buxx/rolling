# coding: utf-8
import dataclasses

import serpyco
from sqlalchemy.orm.exc import NoResultFound
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithCharacterAction
from rolling.action.base import get_with_character_action_url
from rolling.exception import ImpossibleAction
from rolling.model.character import CharacterModel
from rolling.model.event import StoryPage
from rolling.model.fight import AttackDescription
from rolling.model.fight import DefendDescription
from rolling.rolling_types import ActionType
from rolling.server.controller.url import DESCRIBE_LOOK_AT_CHARACTER_URL
from rolling.server.document.affinity import AffinityDocument, CHIEF_STATUS
from rolling.server.document.affinity import MEMBER_STATUS
from rolling.server.document.affinity import WARLORD_STATUS
from rolling.server.document.event import StoryPageDocument
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig


@dataclasses.dataclass
class AttackModel:
    lonely: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    as_affinity: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    confirm: int = serpyco.number_field(cast_on_load=True, default=0)


class AttackCharacterAction(WithCharacterAction):
    input_model = AttackModel
    input_model_serializer = serpyco.Serializer(AttackModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        pass

    def check_request_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: AttackModel
    ) -> None:
        # lonely attack when exhausted is not possible
        if input_.lonely is not None and input_.lonely and not character.is_attack_ready():
            raise ImpossibleAction(f"{character.name} n'est pas en mesure de mener cette attaque !")

        # with_character must not been part of attacking affinity
        if input_.as_affinity is not None and self._kernel.affinity_lib.character_is_in_affinity(
            affinity_id=input_.as_affinity, character_id=with_character.id
        ):
            raise ImpossibleAction(f"Vous ne pouvez pas attaquer un membre d'une même affinités")

        # It must have ready fighter to fight
        if input_.as_affinity is not None and not self._kernel.affinity_lib.count_ready_fighter(
            affinity_id=input_.as_affinity,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
        ):
            raise ImpossibleAction(f"Personne n'est en état de se battre actuellement")

    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name=f"Attaquer", link=self._get_here_url(character, with_character), cost=0.0
            )
        ]

    def _get_here_url(self, character: "CharacterModel", with_character: "CharacterModel") -> str:
        return get_with_character_action_url(
            character_id=character.id,
            with_character_id=with_character.id,
            action_type=ActionType.ATTACK_CHARACTER,
            query_params={},
            action_description_id=self._description.id,
        )

    def _get_root_description(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> Description:
        here_url = self._get_here_url(character, with_character)
        parts = []

        for affinity_relation in self._kernel.affinity_lib.get_accepted_affinities(
            character.id, warlord=True
        ):
            affinity = self._kernel.affinity_lib.get_affinity(affinity_relation.affinity_id)
            parts.append(
                Part(
                    is_link=True,
                    form_action=here_url + f"&as_affinity={affinity.id}",
                    label=f"Attaquer en tant que {affinity.name}",
                )
            )

        return Description(
            title=f"Attaquer {with_character.name}",
            items=[
                Part(text="Veuillez préciser votre intention:"),
                Part(
                    is_link=True,
                    form_action=here_url + "&lonely=1",
                    label="Attaquer seul et en mon nom uniquement",
                ),
            ]
            + parts,
            footer_with_character_id=character.id,
            can_be_back_url=True,
        )

    def _get_attack_lonely_description(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> Description:
        here_url = self._get_here_url(character, with_character)
        defense_description: DefendDescription = self._kernel.fight_lib.get_defense_description(
            origin_target=with_character,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
        )
        aff = ", ".join([a.name for a in defense_description.affinities])
        self._check_attack_lonely(character, defense_description, aff)

        if 1 == len(defense_description.all_fighters):
            fighter = defense_description.all_fighters[0]
            text = f"Engager ce combat implique de vous battre contre {fighter.name} seul à seul"
        else:
            fighters = defense_description.all_fighters
            text = (
                f"Engager ce combat implique de vous battre contre {len(fighters)} combattants "
                f"appartenants aux affinités: {aff}"
            )
        return Description(
            title=f"Attaquer {with_character.name} seul",
            footer_with_character_id=character.id,
            items=[
                Part(text=text),
                Part(
                    is_link=True,
                    form_action=here_url + "&lonely=1&confirm=1",
                    label=f"Je confirme, attaquer {with_character.name} maintenant !",
                ),
            ],
        )

    def _check_attack_lonely(
        self, character: CharacterModel, defense: DefendDescription, aff: str
    ) -> None:
        if not character.is_attack_ready():
            raise ImpossibleAction("Vous n'etes pas en état de vous battre")

        # by affinities, character can be in defense side. In that case, don't permit the fight
        if character.id in [f.id for f in defense.all_fighters]:
            raise ImpossibleAction(
                "Vous ne pouvez pas mener cette attaque car parmis les defenseur se trouve "
                f"des personnes avec lesquelles vous etes affiliés. Affinités en défense: {aff}"
            )

    def _perform_attack_lonely(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> Description:
        defense_description: DefendDescription = self._kernel.fight_lib.get_defense_description(
            origin_target=with_character,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
        )
        aff = ", ".join([a.name for a in defense_description.affinities])
        self._check_attack_lonely(character, defense_description, aff)

        story = self._kernel.fight_lib.fight(
            attack=AttackDescription(all_fighters=[character], ready_fighters=[character]),
            defense=defense_description,
        )
        parts = [Part(text=p) for p in story]

        self._proceed_events(
            attacker_title="Vous avez participé à un combat",
            attacked_title="Vous avez subit une attaque",
            characters=[character] + defense_description.all_fighters,
            author=character,
            story=story,
        )
        self._kill_deads([character] + defense_description.all_fighters)

        return Description(
            title=f"Attaquer {with_character.name} seul",
            footer_with_character_id=character.id,
            items=parts,
        )

    def _proceed_events(
        self,
        attacker_title: str,
        attacked_title: str,
        characters: typing.List[CharacterModel],
        author: CharacterModel,
        story: typing.List[str],
    ) -> None:
        for character in characters:
            title = attacker_title if character == author else attacked_title
            read = character == author

            self._kernel.character_lib.add_event(
                character.id,
                title=title,
                read=read,
                story_pages=[StoryPageDocument(text="\n".join([p for p in story]))],
            )

    def _get_attack_defense_pair(
        self,
        target: CharacterModel,
        as_affinity: AffinityDocument,
        world_row_i: int,
        world_col_i: int,
    ) -> typing.Tuple[AttackDescription, DefendDescription]:
        defense_description: DefendDescription = self._kernel.fight_lib.get_defense_description(
            origin_target=target,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
            attacker_affinity=as_affinity,
        )
        attack_description: AttackDescription = self._kernel.fight_lib.get_attack_description(
            target=defense_description,
            attacker=as_affinity,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
        )

        # remove attacker in conflict from defense
        defense_description.reduce_fighters(attack_description.all_fighters)
        defense_description.reduce_affinities([attack_description.affinity])

        return attack_description, defense_description

    def _check_attack_as_affinity(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        as_affinity: AffinityDocument,
        attack_description: AttackDescription,
        defense_description: DefendDescription,
    ):
        title = f"Attaquer {with_character.name} en tant que {as_affinity.name}"
        here_url = self._get_here_url(character, with_character)

        character_relation = self._kernel.affinity_lib.get_active_relation(
            character_id=character.id, affinity_id=as_affinity.id
        )
        if character_relation.status_id not in (MEMBER_STATUS[0], WARLORD_STATUS[0], CHIEF_STATUS[0]):
            raise ImpossibleAction(
                "Vous ne pouvez impliquer cette affinité qu'avec le role de Chef ou Chef de guerre"
            )

        try:
            self._kernel.affinity_lib.get_active_relation(
                character_id=with_character.id, affinity_id=as_affinity.id
            )
            return Description(
                title=title,
                footer_with_character_id=character.id,
                items=[
                    Part(
                        text=f"Vous ne pouvez pas attaquer {with_character.name} "
                        f"en tant que {as_affinity.name} car il/elle est affilié à "
                        f"{as_affinity.name}"
                    )
                ],
            )
        except NoResultFound:
            pass

        parts = []
        in_conflict_strs: typing.List[str] = []

        for fighter in attack_description.all_fighters:
            if fighter.id in defense_description.helpers:
                affinities_str = ", ".join(
                    [a.name for a in defense_description.helpers[fighter.id]]
                )
                in_conflict_strs.append(f"{fighter.name}, car affilié à: {affinities_str}")

        if in_conflict_strs:
            parts.append(
                Part(
                    text=f"Le combat ne peut avoir lieu car des membres de votre parti ont des "
                    f"affinités avec les defenseurs:"
                )
            )
            for in_conflict_str in in_conflict_strs:
                parts.append(Part(text=f"- {in_conflict_str}"))

            return Description(
                title=title,
                items=parts,
                footer_with_character_id=character.id,
            )

    def _get_attack_as_affinity_description(
        self, character: "CharacterModel", with_character: "CharacterModel", as_affinity_id: int
    ) -> Description:
        here_url = self._get_here_url(character, with_character)
        as_affinity = self._kernel.affinity_lib.get_affinity(as_affinity_id)
        title = f"Attaquer {with_character.name} en tant que {as_affinity.name}"

        attack_description, defense_description = self._get_attack_defense_pair(
            target=with_character,
            as_affinity=as_affinity,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
        )

        resp = self._check_attack_as_affinity(
            character=character,
            with_character=with_character,
            as_affinity=as_affinity,
            attack_description=attack_description,
            defense_description=defense_description,
        )
        if resp:
            return resp

        defense_affinities_str = ""
        if defense_description.affinities:
            aff = ", ".join([f.name for f in defense_description.affinities])
            defense_affinities_str = f" représenté(s) par le/les afinité(s): {aff}"

        defense_text = (
            f"Le parti adverse compte "
            f"{len(defense_description.all_fighters)} combattant(s)"
            f"{defense_affinities_str}"
        )
        attack_text = (
            f"Votre parti est composé de {len(attack_description.all_fighters)} combattat(s) "
            f"dont {len(attack_description.ready_fighters)} en état de combattre"
        )

        return Description(
            title=title,
            items=[
                Part(text=attack_text),
                Part(text=defense_text),
                Part(
                    is_link=True,
                    form_action=here_url + f"&as_affinity={as_affinity_id}&confirm=1",
                    label=f"Je confirme, attaquer {with_character.name} maintenant !",
                ),
            ],
            footer_with_character_id=character.id,
        )

    def _perform_attack_as_affinity(
        self, character: "CharacterModel", with_character: "CharacterModel", as_affinity_id: int
    ) -> Description:
        as_affinity = self._kernel.affinity_lib.get_affinity(as_affinity_id)
        title = f"Attaquer {with_character.name} en tant que {as_affinity.name}"

        attack_description, defense_description = self._get_attack_defense_pair(
            target=with_character,
            as_affinity=as_affinity,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
        )

        resp = self._check_attack_as_affinity(
            character=character,
            with_character=with_character,
            as_affinity=as_affinity,
            attack_description=attack_description,
            defense_description=defense_description,
        )
        if resp:
            return resp

        story = self._kernel.fight_lib.fight(attack=attack_description, defense=defense_description)
        parts = [Part(text=p) for p in story]

        self._proceed_events(
            attacker_title="Vous avez participé à une attaque",
            attacked_title="Vous avez subit une attaque",
            characters=attack_description.all_fighters + defense_description.all_fighters,
            author=character,
            story=story,
        )
        self._kill_deads(attack_description.all_fighters + defense_description.all_fighters)

        return Description(
            title=title,
            items=parts,
            footer_with_character_id=character.id,
        )

    def perform(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: AttackModel
    ) -> Description:
        if input_.lonely is None and input_.as_affinity is None:
            return self._get_root_description(character, with_character)
        elif input_.lonely:
            if not input_.confirm:
                return self._get_attack_lonely_description(character, with_character)
            else:
                return self._perform_attack_lonely(character, with_character)
        elif input_.as_affinity:
            if not input_.confirm:
                return self._get_attack_as_affinity_description(
                    character, with_character, as_affinity_id=input_.as_affinity
                )
            else:
                return self._perform_attack_as_affinity(
                    character, with_character, as_affinity_id=input_.as_affinity
                )

    def _kill_deads(self, check_characters: typing.List[CharacterModel]) -> None:
        for check_character in check_characters:
            if check_character.life_points <= 0:
                self._kernel.character_lib.kill(check_character.id)
