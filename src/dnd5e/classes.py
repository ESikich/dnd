from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, TypeVar

from dnd5e.types import Ability, ArmorTraining, CharacterClassName, Skill, WeaponTraining

ABILITIES: tuple[Ability, ...] = ("str", "dex", "con", "int", "wis", "cha")
ARMOR_TRAINING: tuple[ArmorTraining, ...] = ("light", "medium", "heavy", "shield")
CLASS_NAMES: tuple[CharacterClassName, ...] = (
    "barbarian",
    "bard",
    "cleric",
    "druid",
    "fighter",
    "monk",
    "paladin",
    "ranger",
    "rogue",
    "sorcerer",
    "warlock",
    "wizard",
)
SKILLS: tuple[Skill, ...] = (
    "acrobatics",
    "animal_handling",
    "arcana",
    "athletics",
    "deception",
    "history",
    "insight",
    "intimidation",
    "investigation",
    "medicine",
    "nature",
    "perception",
    "performance",
    "persuasion",
    "religion",
    "sleight_of_hand",
    "stealth",
    "survival",
)
WEAPON_TRAINING: tuple[WeaponTraining, ...] = ("simple", "martial")
T = TypeVar("T")


@dataclass(frozen=True)
class ClassDefinition:
    """Class metadata used by character sheets for hit dice and proficiencies."""

    name: CharacterClassName
    hit_die: int
    primary_abilities: tuple[Ability, ...]
    saving_throws: tuple[Ability, ...]
    armor_training: tuple[ArmorTraining, ...]
    weapon_training: tuple[WeaponTraining, ...]
    skill_choices: tuple[Skill, ...]
    skill_choice_count: int

    def __post_init__(self) -> None:
        if self.name not in CLASS_NAMES:
            raise ValueError(f"unknown class: {self.name}")
        if self.hit_die not in (6, 8, 10, 12):
            raise ValueError("class hit die must be one of d6, d8, d10, or d12")
        _validate_values("primary ability", self.primary_abilities, ABILITIES)
        _validate_values("saving throw", self.saving_throws, ABILITIES)
        _validate_values("armor training", self.armor_training, ARMOR_TRAINING)
        _validate_values("weapon training", self.weapon_training, WEAPON_TRAINING)
        _validate_values("skill choice", self.skill_choices, SKILLS)
        if self.skill_choice_count < 0:
            raise ValueError("skill choice count cannot be negative")
        if self.skill_choice_count > len(self.skill_choices):
            raise ValueError("skill choice count cannot exceed available skill choices")


@dataclass(frozen=True)
class ClassPack:
    """Loaded class content grouped into a class-definition catalog."""

    classes: dict[CharacterClassName, ClassDefinition]


def _validate_values(name: str, values: tuple[str, ...], allowed: tuple[str, ...]) -> None:
    for value in values:
        if value not in allowed:
            raise ValueError(f"unknown {name}: {value}")


def load_class_pack(path: str | Path) -> ClassPack:
    """Load class definitions from a class content-pack JSON file."""

    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("class content pack must be a JSON object")
    return load_class_pack_data(data)


def load_builtin_class_pack() -> ClassPack:
    """Load the packaged SRD-style class content pack."""

    data_resource = files("dnd5e.data").joinpath("classes.json")
    with data_resource.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("built-in class content pack must be a JSON object")
    return load_class_pack_data(data)


def load_class_pack_data(data: Mapping[str, Any]) -> ClassPack:
    """Validate and construct a class pack from decoded JSON-style data."""

    _validate_pack_keys(data)
    return ClassPack(classes=_load_class_entries(data["classes"]))


def _validate_pack_keys(data: Mapping[str, Any]) -> None:
    expected = {"classes"}
    missing = expected - set(data)
    if missing:
        raise ValueError(f"class content pack missing sections: {', '.join(sorted(missing))}")
    extra = set(data) - expected
    if extra:
        raise ValueError(f"class content pack has unknown sections: {', '.join(sorted(extra))}")


def _load_class_entries(entries: Any) -> dict[CharacterClassName, ClassDefinition]:
    return _catalog_by_name(
        [
            ClassDefinition(
                name=_field(entry, "name", str, "class"),  # type: ignore[arg-type]
                hit_die=_field(entry, "hit_die", int, "class"),
                primary_abilities=tuple(_string_list_field(entry, "primary_abilities", "class")),  # type: ignore[arg-type]
                saving_throws=tuple(_string_list_field(entry, "saving_throws", "class")),  # type: ignore[arg-type]
                armor_training=tuple(_string_list_field(entry, "armor_training", "class")),  # type: ignore[arg-type]
                weapon_training=tuple(_string_list_field(entry, "weapon_training", "class")),  # type: ignore[arg-type]
                skill_choices=tuple(_string_list_field(entry, "skill_choices", "class")),  # type: ignore[arg-type]
                skill_choice_count=_field(entry, "skill_choice_count", int, "class"),
            )
            for entry in _validated_entries(
                entries,
                {
                    "name",
                    "hit_die",
                    "primary_abilities",
                    "saving_throws",
                    "armor_training",
                    "weapon_training",
                    "skill_choices",
                    "skill_choice_count",
                },
            )
        ]
    )


def _validated_entries(entries: Any, expected_fields: set[str]) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(entries, list):
        raise ValueError("class content section classes must be a list")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("class content section classes entries must be objects")
        extra = set(entry) - expected_fields
        if extra:
            raise ValueError(f"class entry has unknown fields: {', '.join(sorted(extra))}")
    return tuple(entries)


def _catalog_by_name(entries: list[ClassDefinition]) -> dict[CharacterClassName, ClassDefinition]:
    catalog: dict[CharacterClassName, ClassDefinition] = {}
    for entry in entries:
        if entry.name in catalog:
            raise ValueError(f"duplicate class name: {entry.name}")
        catalog[entry.name] = entry
    return catalog


def _field(entry: Mapping[str, Any], name: str, expected_type: type[T], section: str) -> T:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__}")
    return value


def _string_list_field(entry: Mapping[str, Any], name: str, section: str) -> tuple[str, ...]:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, list):
        raise ValueError(f"{section}.{name} must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{section}.{name} entries must be strings")
    return tuple(value)


_BUILTIN_CLASSES = load_builtin_class_pack()
SRD_CLASSES: dict[CharacterClassName, ClassDefinition] = _BUILTIN_CLASSES.classes
