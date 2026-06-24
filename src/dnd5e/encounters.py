from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dnd5e.creatures import CREATURES, CreatureDefinition

EncounterDifficulty = Literal["trivial", "easy", "medium", "hard", "deadly"]

XP_BY_CHALLENGE_RATING: dict[str, int] = {
    "0": 10,
    "1/8": 25,
    "1/4": 50,
    "1/2": 100,
    "1": 200,
    "2": 450,
    "3": 700,
    "4": 1_100,
    "5": 1_800,
    "6": 2_300,
    "7": 2_900,
    "8": 3_900,
    "9": 5_000,
    "10": 5_900,
    "11": 7_200,
    "12": 8_400,
    "13": 10_000,
    "14": 11_500,
    "15": 13_000,
    "16": 15_000,
    "17": 18_000,
    "18": 20_000,
    "19": 22_000,
    "20": 25_000,
    "21": 33_000,
    "22": 41_000,
    "23": 50_000,
    "24": 62_000,
    "25": 75_000,
    "26": 90_000,
    "27": 105_000,
    "28": 120_000,
    "29": 135_000,
    "30": 155_000,
}


@dataclass(frozen=True)
class EncounterThresholds:
    """Party XP thresholds used to classify encounter difficulty."""

    easy: int
    medium: int
    hard: int
    deadly: int

    def __post_init__(self) -> None:
        if min(self.easy, self.medium, self.hard, self.deadly) < 0:
            raise ValueError("encounter thresholds cannot be negative")
        if not self.easy <= self.medium <= self.hard <= self.deadly:
            raise ValueError("encounter thresholds must be ordered")


@dataclass(frozen=True)
class EncounterMonster:
    """A creature definition and count for encounter XP math."""

    definition: CreatureDefinition
    count: int = 1

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("encounter monster count must be positive")

    @property
    def xp(self) -> int:
        return self.definition.xp * self.count


@dataclass(frozen=True)
class EncounterSummary:
    """A mechanics-first encounter summary with raw XP, adjusted XP, and difficulty."""

    monsters: tuple[EncounterMonster, ...]
    party_levels: tuple[int, ...]
    thresholds: EncounterThresholds
    total_xp: int
    adjusted_xp: float
    xp_multiplier: float
    difficulty: EncounterDifficulty

    def __post_init__(self) -> None:
        if not self.monsters:
            raise ValueError("encounter summary requires at least one monster")
        _validate_party_levels(self.party_levels)
        if self.total_xp < 0:
            raise ValueError("encounter total XP cannot be negative")
        if self.adjusted_xp < self.total_xp:
            raise ValueError("encounter adjusted XP cannot be less than total XP")
        if self.xp_multiplier < 1:
            raise ValueError("encounter XP multiplier must be at least 1")

    @property
    def monster_count(self) -> int:
        return sum(monster.count for monster in self.monsters)


_THRESHOLDS_BY_LEVEL: dict[int, EncounterThresholds] = {
    1: EncounterThresholds(25, 50, 75, 100),
    2: EncounterThresholds(50, 100, 150, 200),
    3: EncounterThresholds(75, 150, 225, 400),
    4: EncounterThresholds(125, 250, 375, 500),
    5: EncounterThresholds(250, 500, 750, 1_100),
    6: EncounterThresholds(300, 600, 900, 1_400),
    7: EncounterThresholds(350, 750, 1_100, 1_700),
    8: EncounterThresholds(450, 900, 1_400, 2_100),
    9: EncounterThresholds(550, 1_100, 1_600, 2_400),
    10: EncounterThresholds(600, 1_200, 1_900, 2_800),
    11: EncounterThresholds(800, 1_600, 2_400, 3_600),
    12: EncounterThresholds(1_000, 2_000, 3_000, 4_500),
    13: EncounterThresholds(1_100, 2_200, 3_400, 5_100),
    14: EncounterThresholds(1_250, 2_500, 3_800, 5_700),
    15: EncounterThresholds(1_400, 2_800, 4_300, 6_400),
    16: EncounterThresholds(1_600, 3_200, 4_800, 7_200),
    17: EncounterThresholds(2_000, 3_900, 5_900, 8_800),
    18: EncounterThresholds(2_100, 4_200, 6_300, 9_500),
    19: EncounterThresholds(2_400, 4_900, 7_300, 10_900),
    20: EncounterThresholds(2_800, 5_700, 8_500, 12_700),
}


def challenge_rating_xp(challenge_rating: str) -> int:
    """Return the XP award for a challenge rating."""

    try:
        return XP_BY_CHALLENGE_RATING[challenge_rating]
    except KeyError as error:
        raise ValueError(f"unknown challenge rating: {challenge_rating}") from error


def encounter_monster(
    definition: str | CreatureDefinition,
    *,
    count: int = 1,
) -> EncounterMonster:
    """Create a counted encounter monster from a catalog id or creature definition."""

    creature = CREATURES[definition] if isinstance(definition, str) else definition
    return EncounterMonster(definition=creature, count=count)


def encounter_xp_multiplier(monster_count: int) -> float:
    """Return the encounter XP multiplier for a number of monsters."""

    if monster_count < 1:
        raise ValueError("monster count must be positive")
    if monster_count == 1:
        return 1
    if monster_count == 2:
        return 1.5
    if monster_count <= 6:
        return 2
    if monster_count <= 10:
        return 2.5
    if monster_count <= 14:
        return 3
    return 4


def party_xp_thresholds(party_levels: tuple[int, ...] | list[int]) -> EncounterThresholds:
    """Return combined encounter XP thresholds for a party."""

    levels = tuple(party_levels)
    _validate_party_levels(levels)

    return EncounterThresholds(
        easy=sum(_THRESHOLDS_BY_LEVEL[level].easy for level in levels),
        medium=sum(_THRESHOLDS_BY_LEVEL[level].medium for level in levels),
        hard=sum(_THRESHOLDS_BY_LEVEL[level].hard for level in levels),
        deadly=sum(_THRESHOLDS_BY_LEVEL[level].deadly for level in levels),
    )


def encounter_difficulty(
    adjusted_xp: float,
    thresholds: EncounterThresholds,
) -> EncounterDifficulty:
    """Classify adjusted encounter XP against party thresholds."""

    if adjusted_xp < 0:
        raise ValueError("adjusted XP cannot be negative")
    if adjusted_xp >= thresholds.deadly:
        return "deadly"
    if adjusted_xp >= thresholds.hard:
        return "hard"
    if adjusted_xp >= thresholds.medium:
        return "medium"
    if adjusted_xp >= thresholds.easy:
        return "easy"
    return "trivial"


def summarize_encounter(
    monsters: tuple[EncounterMonster, ...] | list[EncounterMonster],
    *,
    party_levels: tuple[int, ...] | list[int],
) -> EncounterSummary:
    """Summarize monster XP, adjusted XP, thresholds, and difficulty for a party."""

    monster_groups = tuple(monsters)
    if not monster_groups:
        raise ValueError("encounter requires at least one monster")

    thresholds = party_xp_thresholds(party_levels)
    total_xp = sum(monster.xp for monster in monster_groups)
    multiplier = encounter_xp_multiplier(sum(monster.count for monster in monster_groups))
    adjusted_xp = total_xp * multiplier

    return EncounterSummary(
        monsters=monster_groups,
        party_levels=tuple(party_levels),
        thresholds=thresholds,
        total_xp=total_xp,
        adjusted_xp=adjusted_xp,
        xp_multiplier=multiplier,
        difficulty=encounter_difficulty(adjusted_xp, thresholds),
    )


def _validate_party_levels(levels: tuple[int, ...]) -> None:
    if not levels:
        raise ValueError("party levels are required")
    for level in levels:
        if not 1 <= level <= 20:
            raise ValueError("party levels must be from 1 to 20")
