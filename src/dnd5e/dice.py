from __future__ import annotations

import re
from dataclasses import dataclass
from random import random

from dnd5e.abilities import RandomSource, random_die

_DICE_PATTERN = re.compile(r"^(\d*)d(\d+)([+-]\d+)?$", re.IGNORECASE)


@dataclass(frozen=True)
class DiceNotation:
    """Parsed ``XdY+Z`` dice expression used by roll and average helpers."""

    count: int
    sides: int
    modifier: int


@dataclass(frozen=True)
class DiceRoll:
    """Concrete result of rolling one dice expression."""

    notation: str
    rolls: tuple[int, ...]
    modifier: int
    total: int


def parse_dice_notation(notation: str) -> DiceNotation:
    """Parse basic dice notation such as ``d20``, ``2d6+3``, or ``4d8-1``."""

    match = _DICE_PATTERN.match(notation.strip())
    if not match:
        raise ValueError(f"invalid dice notation: {notation}")

    count = int(match.group(1) or "1")
    sides = int(match.group(2))
    modifier = int(match.group(3) or "0")

    if count < 1:
        raise ValueError("dice count must be positive")

    if sides < 2:
        raise ValueError("dice sides must be at least 2")

    return DiceNotation(count=count, sides=sides, modifier=modifier)


def roll_dice(notation: str, *, rng: RandomSource = random) -> DiceRoll:
    """Roll a dice expression and return each die plus the final total."""

    parsed = parse_dice_notation(notation)
    rolls = tuple(random_die(parsed.sides, rng) for _ in range(parsed.count))

    return DiceRoll(
        notation=notation,
        rolls=rolls,
        modifier=parsed.modifier,
        total=sum(rolls) + parsed.modifier,
    )


def average_dice(notation: str) -> float:
    """Return the statistical average for a dice expression."""

    parsed = parse_dice_notation(notation)
    return parsed.count * ((parsed.sides + 1) / 2) + parsed.modifier
