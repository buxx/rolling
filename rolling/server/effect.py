# coding: utf-8
import typing

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.effect import CharacterEffectDescriptionModel
    from rolling.server.document.character import CharacterDocument


class EffectManager:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def enable_effect(
        self, character_doc: "CharacterDocument", effect: "CharacterEffectDescriptionModel"
    ) -> None:
        for attr_name in effect.attributes_to_false:
            setattr(character_doc, attr_name, False)

        for attr_name in effect.attributes_to_true:
            setattr(character_doc, attr_name, True)

        effect_ids = character_doc.effect_ids
        effect_ids.append(effect.id)
        character_doc.effect_ids = effect_ids
