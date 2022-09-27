import dataclasses
import typing

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.stuff import StuffModel
    from rolling.model.character import CharacterSkillModel


@dataclasses.dataclass
class Bonus:
    coefficient: float
    from_stuff: typing.Optional["StuffModel"] = None
    from_skill: typing.Optional["CharacterSkillModel"] = None

    def name(self) -> str:
        if self.from_stuff is not None:
            return f"{self.from_stuff.name} (PAx{round(self.coefficient, 3)})"

        if self.from_skill is not None:
            return f"{self.from_skill.name} (PAx{round(self.coefficient, 3)})"

        return "N/A"


@dataclasses.dataclass
class Bonuses:
    bonuses: typing.List[Bonus]

    def names(self) -> typing.List[str]:
        return [bonus.name() for bonus in self.bonuses]

    def apply(self, action_points: float) -> float:
        for bonus in self.bonuses:
            action_points = action_points * bonus.coefficient
        return action_points
