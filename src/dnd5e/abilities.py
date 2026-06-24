from __future__ import annotations

from dataclasses import dataclass
from random import random
from typing import Callable

from dnd5e.types import AdvantageState, ProficiencyLevel

RandomSource = Callable[[], float]


@dataclass(frozen=True)
class D20CheckResult:
    roll: int
    modifier: int
    proficiency: int
    bonus: int
    total: int
    natural_one: bool
    natural_twenty: bool
    discarded_roll: int | None = None


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def proficiency_bonus(level: int) -> int:
    if not 1 <= level <= 20:
        raise ValueError("level must be from 1 to 20")

    return 2 + ((level - 1) // 4)


def proficiency_value(proficiency: ProficiencyLevel, bonus: int) -> int:
    multipliers: dict[ProficiencyLevel, float] = {
        "none": 0,
        "half": 0.5,
        "proficient": 1,
        "expertise": 2,
    }
    return int(multipliers[proficiency] * bonus)


def passive_score(modifier: int, proficiency: int = 0, bonus: int = 0) -> int:
    return 10 + modifier + proficiency + bonus


def d20_check(
    *,
    ability_score: int,
    proficiency_bonus_value: int = 0,
    proficiency: ProficiencyLevel = "none",
    bonus: int = 0,
    roll: int | None = None,
    advantage: AdvantageState = "normal",
    rng: RandomSource = random,
) -> D20CheckResult:
    kept, discarded = _roll_d20(roll=roll, advantage=advantage, rng=rng)
    modifier = ability_modifier(ability_score)
    proficiency_amount = proficiency_value(proficiency, proficiency_bonus_value)
    total = kept + modifier + proficiency_amount + bonus

    return D20CheckResult(
        roll=kept,
        discarded_roll=discarded,
        modifier=modifier,
        proficiency=proficiency_amount,
        bonus=bonus,
        total=total,
        natural_one=kept == 1,
        natural_twenty=kept == 20,
    )


def random_die(sides: int, rng: RandomSource = random) -> int:
    if sides < 1:
        raise ValueError("sides must be positive")

    return int(rng() * sides) + 1


def _roll_d20(
    *,
    roll: int | None,
    advantage: AdvantageState,
    rng: RandomSource,
) -> tuple[int, int | None]:
    if roll is not None:
        if not 1 <= roll <= 20:
            raise ValueError("roll must be from 1 to 20")
        return roll, None

    first = random_die(20, rng)

    if advantage == "normal":
        return first, None

    second = random_die(20, rng)
    return (max(first, second), min(first, second)) if advantage == "advantage" else (
        min(first, second),
        max(first, second),
    )
