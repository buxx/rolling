# coding: utf-8
import dataclasses

DEFAULT_MAXIMUM_SKILL = 5.0


@dataclasses.dataclass
class SkillDescription:
    id: str
    name: str
    default: float
    maximum: float


@dataclasses.dataclass
class CharacterSkillModel:
    id: str
    name: str
    value: float
    counter: float

    def as_ap_bonus(self) -> float:
        """
        skill value is a math.log (base 4, see DEFAULT_LOG_BASE). values likes (counter value):
         * 1 0.0
         * 10 1.66
         * 100 3.32
         * 500 4.48
         * 1000 4,98
        """
        if self.value < 1.0:
            # No bonus
            return 1.0

        # Maximum of skill is DEFAULT_MAXIMUM_SKILL
        value = min(DEFAULT_MAXIMUM_SKILL, self.value)

        # Consider maximum AP bonus is 0.5
        return 1.0 - (0.5 * (value / DEFAULT_MAXIMUM_SKILL))
