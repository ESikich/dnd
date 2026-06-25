from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, TypeVar

from dnd5e.types import Ability, CreatureSize

ABILITIES: tuple[Ability, ...] = ("str", "dex", "con", "int", "wis", "cha")
SIZES: tuple[CreatureSize, ...] = ("tiny", "small", "medium", "large", "huge", "gargantuan")
T = TypeVar("T")


@dataclass(frozen=True)
class AncestryAbilityBonus:
    """An ability score bonus granted by a race, subrace, or ancestry option."""

    ability: Ability
    bonus: int

    def __post_init__(self) -> None:
        if self.ability not in ABILITIES:
            raise ValueError(f"unknown ability: {self.ability}")


@dataclass(frozen=True)
class RaceDefinition:
    """Compact race metadata for speed, size, languages, traits, and ability bonuses."""

    id: str
    name: str
    speed: int
    size: CreatureSize
    ability_bonuses: tuple[AncestryAbilityBonus, ...]
    ability_bonus_options: tuple[AncestryAbilityBonus, ...] = ()
    ability_bonus_choice_count: int = 0
    languages: tuple[str, ...] = ()
    language_options: tuple[str, ...] = ()
    language_choice_count: int = 0
    traits: tuple[str, ...] = ()
    subraces: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "race")
        if self.speed < 0:
            raise ValueError("race speed cannot be negative")
        if self.size not in SIZES:
            raise ValueError(f"unknown race size: {self.size}")
        _validate_choice_count(
            "ability bonus choice count",
            self.ability_bonus_choice_count,
            len(self.ability_bonus_options),
        )
        _validate_choice_count(
            "language choice count",
            self.language_choice_count,
            len(self.language_options),
        )


@dataclass(frozen=True)
class SubraceDefinition:
    """Compact subrace metadata that can be layered onto a parent race."""

    id: str
    name: str
    race_id: str
    ability_bonuses: tuple[AncestryAbilityBonus, ...]
    traits: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "subrace")
        _validate_id(self.race_id, "subrace race")


@dataclass(frozen=True)
class LanguageDefinition:
    """Language metadata with type, script, and typical speaker categories."""

    id: str
    name: str
    type: str
    script: str | None = None
    typical_speakers: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "language")
        if not self.name:
            raise ValueError("language name is required")
        if not self.type:
            raise ValueError("language type is required")


@dataclass(frozen=True)
class ProficiencyDefinition:
    """Proficiency metadata linked to its referenced rules object."""

    id: str
    name: str
    type: str
    reference_id: str | None = None
    reference_url: str | None = None
    class_ids: tuple[str, ...] = ()
    race_ids: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "proficiency")
        if not self.name:
            raise ValueError("proficiency name is required")
        if not self.type:
            raise ValueError("proficiency type is required")


@dataclass(frozen=True)
class AncestryPack:
    """Loaded ancestry content grouped into race, subrace, language, and proficiency catalogs."""

    races: dict[str, RaceDefinition]
    subraces: dict[str, SubraceDefinition]
    languages: dict[str, LanguageDefinition]
    proficiencies: dict[str, ProficiencyDefinition]


def load_ancestry_pack(path: str | Path) -> AncestryPack:
    """Load ancestry definitions from a content-pack JSON file."""

    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("ancestry content pack must be a JSON object")
    return load_ancestry_pack_data(data)


def load_builtin_ancestry_pack() -> AncestryPack:
    """Load the packaged SRD-style ancestry content pack."""

    data_resource = files("dnd5e.data").joinpath("ancestries.json")
    with data_resource.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("built-in ancestry content pack must be a JSON object")
    return load_ancestry_pack_data(data)


def load_ancestry_pack_data(data: Mapping[str, Any]) -> AncestryPack:
    """Validate and construct an ancestry pack from decoded JSON-style data."""

    _validate_pack_keys(data)
    return AncestryPack(
        races=_catalog_by_id(_load_race_entries(data["races"]), "race"),
        subraces=_catalog_by_id(_load_subrace_entries(data["subraces"]), "subrace"),
        languages=_catalog_by_id(_load_language_entries(data["languages"]), "language"),
        proficiencies=_catalog_by_id(_load_proficiency_entries(data["proficiencies"]), "proficiency"),
    )


def race_ability_bonuses(
    race: str | RaceDefinition,
    *,
    subrace: str | SubraceDefinition | None = None,
    ability_choices: tuple[Ability, ...] = (),
) -> dict[Ability, int]:
    """Return combined race, optional subrace, and chosen ability bonuses."""

    race_definition = _resolve_race(race)
    _validate_ability_choices(race_definition, ability_choices)
    bonuses = _bonus_map(race_definition.ability_bonuses)
    for ability in ability_choices:
        option = _ability_option(race_definition, ability)
        bonuses[ability] = bonuses.get(ability, 0) + option.bonus
    if subrace is not None:
        subrace_definition = _resolve_subrace(subrace)
        if subrace_definition.race_id != race_definition.id:
            raise ValueError("subrace does not belong to race")
        _add_bonuses(bonuses, subrace_definition.ability_bonuses)
    return bonuses


def race_languages(
    race: str | RaceDefinition,
    *,
    language_choices: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Return fixed race languages plus validated selected language options."""

    race_definition = _resolve_race(race)
    if len(language_choices) != race_definition.language_choice_count:
        raise ValueError("incorrect number of language choices")
    invalid = set(language_choices) - set(race_definition.language_options)
    if invalid:
        raise ValueError(f"invalid language choices: {', '.join(sorted(invalid))}")
    return tuple(dict.fromkeys((*race_definition.languages, *language_choices)))


def _validate_pack_keys(data: Mapping[str, Any]) -> None:
    expected = {"races", "subraces", "languages", "proficiencies"}
    missing = expected - set(data)
    if missing:
        raise ValueError(f"ancestry content pack missing sections: {', '.join(sorted(missing))}")
    extra = set(data) - expected
    if extra:
        raise ValueError(f"ancestry content pack has unknown sections: {', '.join(sorted(extra))}")


def _load_race_entries(entries: Any) -> list[RaceDefinition]:
    return [
        RaceDefinition(
            id=_field(entry, "id", str, "race"),
            name=_field(entry, "name", str, "race"),
            speed=_field(entry, "speed", int, "race"),
            size=_field(entry, "size", str, "race"),  # type: ignore[arg-type]
            ability_bonuses=_ability_bonus_entries(entry, "ability_bonuses", "race"),
            ability_bonus_options=_ability_bonus_entries(entry, "ability_bonus_options", "race"),
            ability_bonus_choice_count=_field(entry, "ability_bonus_choice_count", int, "race"),
            languages=_string_tuple_field(entry, "languages", "race"),
            language_options=_string_tuple_field(entry, "language_options", "race"),
            language_choice_count=_field(entry, "language_choice_count", int, "race"),
            traits=_string_tuple_field(entry, "traits", "race"),
            subraces=_string_tuple_field(entry, "subraces", "race"),
            source_url=_optional_field(entry, "source_url", str, "race"),
        )
        for entry in _validated_entries(
            entries,
            "races",
            {
                "id",
                "name",
                "speed",
                "size",
                "ability_bonuses",
                "ability_bonus_options",
                "ability_bonus_choice_count",
                "languages",
                "language_options",
                "language_choice_count",
                "traits",
                "subraces",
                "source_url",
            },
        )
    ]


def _load_subrace_entries(entries: Any) -> list[SubraceDefinition]:
    return [
        SubraceDefinition(
            id=_field(entry, "id", str, "subrace"),
            name=_field(entry, "name", str, "subrace"),
            race_id=_field(entry, "race_id", str, "subrace"),
            ability_bonuses=_ability_bonus_entries(entry, "ability_bonuses", "subrace"),
            traits=_string_tuple_field(entry, "traits", "subrace"),
            source_url=_optional_field(entry, "source_url", str, "subrace"),
        )
        for entry in _validated_entries(
            entries,
            "subraces",
            {"id", "name", "race_id", "ability_bonuses", "traits", "source_url"},
        )
    ]


def _load_language_entries(entries: Any) -> list[LanguageDefinition]:
    return [
        LanguageDefinition(
            id=_field(entry, "id", str, "language"),
            name=_field(entry, "name", str, "language"),
            type=_field(entry, "type", str, "language"),
            script=_optional_field(entry, "script", str, "language"),
            typical_speakers=_string_tuple_field(entry, "typical_speakers", "language"),
            source_url=_optional_field(entry, "source_url", str, "language"),
        )
        for entry in _validated_entries(
            entries,
            "languages",
            {"id", "name", "type", "script", "typical_speakers", "source_url"},
        )
    ]


def _load_proficiency_entries(entries: Any) -> list[ProficiencyDefinition]:
    return [
        ProficiencyDefinition(
            id=_field(entry, "id", str, "proficiency"),
            name=_field(entry, "name", str, "proficiency"),
            type=_field(entry, "type", str, "proficiency"),
            reference_id=_optional_field(entry, "reference_id", str, "proficiency"),
            reference_url=_optional_field(entry, "reference_url", str, "proficiency"),
            class_ids=_string_tuple_field(entry, "class_ids", "proficiency"),
            race_ids=_string_tuple_field(entry, "race_ids", "proficiency"),
            source_url=_optional_field(entry, "source_url", str, "proficiency"),
        )
        for entry in _validated_entries(
            entries,
            "proficiencies",
            {
                "id",
                "name",
                "type",
                "reference_id",
                "reference_url",
                "class_ids",
                "race_ids",
                "source_url",
            },
        )
    ]


def _ability_bonus_entries(
    entry: Mapping[str, Any],
    name: str,
    section: str,
) -> tuple[AncestryAbilityBonus, ...]:
    return tuple(
        AncestryAbilityBonus(
            ability=_field(item, "ability", str, "ability bonus"),  # type: ignore[arg-type]
            bonus=_field(item, "bonus", int, "ability bonus"),
        )
        for item in _validated_nested_entries(entry, name, section, {"ability", "bonus"})
    )


def _validated_entries(
    entries: Any, section: str, expected_fields: set[str]
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(entries, list):
        raise ValueError(f"ancestry content section {section} must be a list")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError(f"ancestry content section {section} entries must be objects")
        extra = set(entry) - expected_fields
        if extra:
            raise ValueError(f"{section} entry has unknown fields: {', '.join(sorted(extra))}")
    return tuple(entries)


def _validated_nested_entries(
    entry: Mapping[str, Any],
    name: str,
    section: str,
    expected_fields: set[str],
) -> tuple[Mapping[str, Any], ...]:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, list):
        raise ValueError(f"{section}.{name} must be a list")
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"{section}.{name} entries must be objects")
        extra = set(item) - expected_fields
        if extra:
            raise ValueError(f"{section}.{name} entry has unknown fields: {', '.join(sorted(extra))}")
    return tuple(value)


def _catalog_by_id(entries: list[T], section: str) -> dict[str, T]:
    catalog: dict[str, T] = {}
    for entry in entries:
        id_ = getattr(entry, "id")
        if id_ in catalog:
            raise ValueError(f"duplicate {section} id: {id_}")
        catalog[id_] = entry
    return catalog


def _field(entry: Mapping[str, Any], name: str, expected_type: type[T], section: str) -> T:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__}")
    return value


def _optional_field(
    entry: Mapping[str, Any],
    name: str,
    expected_type: type[T],
    section: str,
) -> T | None:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if value is None:
        return None
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__} or null")
    return value


def _string_tuple_field(entry: Mapping[str, Any], name: str, section: str) -> tuple[str, ...]:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, list):
        raise ValueError(f"{section}.{name} must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{section}.{name} entries must be strings")
    return tuple(value)


def _validate_id(value: str, section: str) -> None:
    if not value:
        raise ValueError(f"{section} id is required")


def _validate_choice_count(name: str, value: int, option_count: int) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative")
    if value > option_count:
        raise ValueError(f"{name} cannot exceed available options")


def _bonus_map(bonuses: tuple[AncestryAbilityBonus, ...]) -> dict[Ability, int]:
    result: dict[Ability, int] = {}
    _add_bonuses(result, bonuses)
    return result


def _add_bonuses(result: dict[Ability, int], bonuses: tuple[AncestryAbilityBonus, ...]) -> None:
    for bonus in bonuses:
        result[bonus.ability] = result.get(bonus.ability, 0) + bonus.bonus


def _ability_option(race: RaceDefinition, ability: Ability) -> AncestryAbilityBonus:
    for option in race.ability_bonus_options:
        if option.ability == ability:
            return option
    raise ValueError(f"invalid ability choice: {ability}")


def _validate_ability_choices(race: RaceDefinition, choices: tuple[Ability, ...]) -> None:
    if len(choices) != race.ability_bonus_choice_count:
        raise ValueError("incorrect number of ability choices")
    if len(set(choices)) != len(choices):
        raise ValueError("ability choices must be unique")
    for ability in choices:
        _ability_option(race, ability)


def _resolve_race(race: str | RaceDefinition) -> RaceDefinition:
    return race if isinstance(race, RaceDefinition) else RACES[race]


def _resolve_subrace(subrace: str | SubraceDefinition) -> SubraceDefinition:
    return subrace if isinstance(subrace, SubraceDefinition) else SUBRACES[subrace]


_BUILTIN_ANCESTRIES = load_builtin_ancestry_pack()
RACES: dict[str, RaceDefinition] = _BUILTIN_ANCESTRIES.races
SUBRACES: dict[str, SubraceDefinition] = _BUILTIN_ANCESTRIES.subraces
LANGUAGES: dict[str, LanguageDefinition] = _BUILTIN_ANCESTRIES.languages
PROFICIENCIES: dict[str, ProficiencyDefinition] = _BUILTIN_ANCESTRIES.proficiencies
