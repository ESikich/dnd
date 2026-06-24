from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from dnd5e.creatures import CREATURES, CreatureDefinition

EncounterDifficulty = Literal["trivial", "easy", "medium", "hard", "deadly"]


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
class EncounterRulesPack:
    """Loaded encounter math tables for CR XP and party difficulty thresholds."""

    challenge_rating_xp: dict[str, int]
    party_thresholds: dict[int, EncounterThresholds]

    def __post_init__(self) -> None:
        if not self.challenge_rating_xp:
            raise ValueError("encounter rules require challenge rating XP entries")
        if not self.party_thresholds:
            raise ValueError("encounter rules require party threshold entries")
        for challenge_rating, xp in self.challenge_rating_xp.items():
            if not challenge_rating:
                raise ValueError("encounter challenge rating cannot be empty")
            if xp < 0:
                raise ValueError("encounter challenge rating XP cannot be negative")
        for level in self.party_thresholds:
            if not 1 <= level <= 20:
                raise ValueError("encounter party threshold levels must be from 1 to 20")


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


def load_encounter_rules_pack(path: str | Path) -> EncounterRulesPack:
    """Load encounter math tables from an encounter content-pack JSON file."""

    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("encounter rules content pack must be a JSON object")
    return load_encounter_rules_pack_data(data)


def load_builtin_encounter_rules_pack() -> EncounterRulesPack:
    """Load the packaged SRD-style encounter math content pack."""

    data_resource = files("dnd5e.data").joinpath("encounters.json")
    with data_resource.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("built-in encounter rules content pack must be a JSON object")
    return load_encounter_rules_pack_data(data)


def load_encounter_rules_pack_data(data: Mapping[str, Any]) -> EncounterRulesPack:
    """Validate and construct encounter math tables from decoded JSON-style data."""

    _validate_pack_keys(data)
    return EncounterRulesPack(
        challenge_rating_xp=_challenge_rating_xp_entries(data["challenge_rating_xp"]),
        party_thresholds=_party_threshold_entries(data["party_thresholds"]),
    )


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
        if level not in _THRESHOLDS_BY_LEVEL:
            raise ValueError(f"missing party threshold for level: {level}")


def _validate_pack_keys(data: Mapping[str, Any]) -> None:
    expected = {"challenge_rating_xp", "party_thresholds"}
    missing = expected - set(data)
    if missing:
        raise ValueError(f"encounter rules content pack missing sections: {', '.join(sorted(missing))}")
    extra = set(data) - expected
    if extra:
        raise ValueError(f"encounter rules content pack has unknown sections: {', '.join(sorted(extra))}")


def _challenge_rating_xp_entries(entries: Any) -> dict[str, int]:
    if not isinstance(entries, Mapping):
        raise ValueError("encounter rules challenge_rating_xp must be an object")
    xp_by_challenge_rating: dict[str, int] = {}
    for challenge_rating, xp in entries.items():
        if not isinstance(challenge_rating, str):
            raise ValueError("encounter rules challenge ratings must be strings")
        if not isinstance(xp, int):
            raise ValueError("encounter rules challenge rating XP values must be integers")
        xp_by_challenge_rating[challenge_rating] = xp
    return xp_by_challenge_rating


def _party_threshold_entries(entries: Any) -> dict[int, EncounterThresholds]:
    thresholds: dict[int, EncounterThresholds] = {}
    for entry in _validated_entries(
        entries,
        "party_thresholds",
        {"level", "easy", "medium", "hard", "deadly"},
    ):
        level = _field(entry, "level", int, "party threshold")
        if level in thresholds:
            raise ValueError(f"duplicate party threshold level: {level}")
        thresholds[level] = EncounterThresholds(
            easy=_field(entry, "easy", int, "party threshold"),
            medium=_field(entry, "medium", int, "party threshold"),
            hard=_field(entry, "hard", int, "party threshold"),
            deadly=_field(entry, "deadly", int, "party threshold"),
        )
    return thresholds


def _validated_entries(
    entries: Any, section: str, expected_fields: set[str]
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(entries, list):
        raise ValueError(f"encounter rules content section {section} must be a list")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError(f"encounter rules content section {section} entries must be objects")
        extra = set(entry) - expected_fields
        if extra:
            raise ValueError(f"{section} entry has unknown fields: {', '.join(sorted(extra))}")
    return tuple(entries)


def _field(entry: Mapping[str, Any], name: str, expected_type: type[int], section: str) -> int:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__}")
    return value


_BUILTIN_ENCOUNTER_RULES = load_builtin_encounter_rules_pack()
XP_BY_CHALLENGE_RATING: dict[str, int] = _BUILTIN_ENCOUNTER_RULES.challenge_rating_xp
_THRESHOLDS_BY_LEVEL: dict[int, EncounterThresholds] = _BUILTIN_ENCOUNTER_RULES.party_thresholds
