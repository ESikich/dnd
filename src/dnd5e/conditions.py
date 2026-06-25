from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, TypeVar

from dnd5e.types import ConditionName, ConditionTag

T = TypeVar("T")

CONDITION_NAMES: tuple[ConditionName, ...] = (
    "blinded",
    "charmed",
    "deafened",
    "exhaustion",
    "frightened",
    "grappled",
    "incapacitated",
    "invisible",
    "paralyzed",
    "petrified",
    "poisoned",
    "prone",
    "restrained",
    "stunned",
    "unconscious",
)
CONDITION_TAGS: tuple[ConditionTag, ...] = (
    "cannot_move",
    "cannot_act",
    "cannot_see",
    "cannot_hear",
    "attack_rolls_affected",
    "ability_checks_affected",
    "saving_throws_affected",
    "speed_zero",
    "melee_attackers_affected",
    "auto_fail_strength_dexterity_saves",
    "critical_hits_from_nearby_attackers",
)


@dataclass(frozen=True)
class ConditionDefinition:
    """Condition metadata as compact mechanical tags for later effect hooks."""

    name: ConditionName
    tags: tuple[ConditionTag, ...]

    def __post_init__(self) -> None:
        if self.name not in CONDITION_NAMES:
            raise ValueError(f"unknown condition: {self.name}")
        for tag in self.tags:
            if tag not in CONDITION_TAGS:
                raise ValueError(f"unknown condition tag: {tag}")


@dataclass(frozen=True)
class ConditionPack:
    """Loaded condition content grouped into a condition-definition catalog."""

    conditions: dict[ConditionName, ConditionDefinition]


def load_condition_pack(path: str | Path) -> ConditionPack:
    """Load condition definitions from a condition content-pack JSON file."""

    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("condition content pack must be a JSON object")
    return load_condition_pack_data(data)


def load_builtin_condition_pack() -> ConditionPack:
    """Load the packaged SRD-style condition content pack."""

    data_resource = files("dnd5e.data").joinpath("conditions.json")
    with data_resource.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("built-in condition content pack must be a JSON object")
    return load_condition_pack_data(data)


def load_condition_pack_data(data: Mapping[str, Any]) -> ConditionPack:
    """Validate and construct a condition pack from decoded JSON-style data."""

    _validate_pack_keys(data)
    return ConditionPack(conditions=_load_condition_entries(data["conditions"]))


def _validate_pack_keys(data: Mapping[str, Any]) -> None:
    expected = {"conditions"}
    missing = expected - set(data)
    if missing:
        raise ValueError(f"condition content pack missing sections: {', '.join(sorted(missing))}")
    extra = set(data) - expected
    if extra:
        raise ValueError(f"condition content pack has unknown sections: {', '.join(sorted(extra))}")


def _load_condition_entries(entries: Any) -> dict[ConditionName, ConditionDefinition]:
    return _catalog_by_name(
        [
            ConditionDefinition(
                name=_field(entry, "name", str, "condition"),  # type: ignore[arg-type]
                tags=_string_tuple_field(entry, "tags", "condition"),  # type: ignore[arg-type]
            )
            for entry in _validated_entries(entries, "conditions", {"name", "tags"})
        ]
    )


def _validated_entries(
    entries: Any, section: str, expected_fields: set[str]
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(entries, list):
        raise ValueError(f"condition content section {section} must be a list")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError(f"condition content section {section} entries must be objects")
        extra = set(entry) - expected_fields
        if extra:
            raise ValueError(f"{section} entry has unknown fields: {', '.join(sorted(extra))}")
    return tuple(entries)


def _catalog_by_name(entries: list[ConditionDefinition]) -> dict[ConditionName, ConditionDefinition]:
    catalog: dict[ConditionName, ConditionDefinition] = {}
    for entry in entries:
        if entry.name in catalog:
            raise ValueError(f"duplicate condition name: {entry.name}")
        catalog[entry.name] = entry
    return catalog


def _field(entry: Mapping[str, Any], name: str, expected_type: type[T], section: str) -> T:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__}")
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


_BUILTIN_CONDITIONS = load_builtin_condition_pack()
CONDITIONS: dict[ConditionName, ConditionDefinition] = _BUILTIN_CONDITIONS.conditions
