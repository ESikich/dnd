from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dnd5e.sheets import CharacterClassLevel, CharacterLoadout, CharacterSheet

CHARACTER_SHEET_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ValidationErrorDetail:
    """One validation error with a dotted JSON path and human-readable message."""

    path: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    """Validation result object for JSON-style import data."""

    errors: tuple[ValidationErrorDetail, ...] = ()

    @property
    def valid(self) -> bool:
        """Return whether validation found no errors."""

        return not self.errors


def character_sheet_to_data(sheet: CharacterSheet) -> dict[str, Any]:
    """Convert a character sheet to JSON-compatible data."""

    return {
        "type": "character_sheet",
        "version": CHARACTER_SHEET_SCHEMA_VERSION,
        "id": sheet.id,
        "name": sheet.name,
        "classes": [
            {"name": class_level.name, "level": class_level.level}
            for class_level in sheet.classes
        ],
        "abilities": dict(sheet.abilities),
        "skill_proficiencies": dict(sheet.skill_proficiencies),
        "saving_throw_proficiencies": dict(sheet.saving_throw_proficiencies),
        "skill_bonuses": dict(sheet.skill_bonuses),
        "saving_throw_bonuses": dict(sheet.saving_throw_bonuses),
        "initiative_bonus_value": sheet.initiative_bonus_value,
        "loadout": {
            "armor": sheet.loadout.armor,
            "shield": sheet.loadout.shield,
            "weapons": list(sheet.loadout.weapons),
            "two_handed_weapons": list(sheet.loadout.two_handed_weapons),
            "armor_class_bonus": sheet.loadout.armor_class_bonus,
            "weapon_attack_bonus": sheet.loadout.weapon_attack_bonus,
        },
        "maximum_hit_points": sheet.maximum_hit_points,
        "current_hit_points": sheet.current_hit_points,
        "temporary_hit_points": sheet.temporary_hit_points,
        "notes": list(sheet.notes),
    }


def character_sheet_from_data(data: Mapping[str, Any]) -> CharacterSheet:
    """Load a character sheet from validated JSON-style data."""

    result = validate_character_sheet_data(data)
    if not result.valid:
        first = result.errors[0]
        raise ValueError(f"{first.path}: {first.message}")

    return _character_sheet_from_validated_data(data)


def _character_sheet_from_validated_data(data: Mapping[str, Any]) -> CharacterSheet:
    classes = data["classes"]
    loadout = data["loadout"]
    if not isinstance(classes, Sequence) or isinstance(classes, str):
        raise ValueError("classes: must be a list")
    if not isinstance(loadout, Mapping):
        raise ValueError("loadout: must be an object")

    return CharacterSheet(
        id=data["id"],
        name=data["name"],
        classes=tuple(
            CharacterClassLevel(name=class_data["name"], level=class_data["level"])
            for class_data in classes
            if isinstance(class_data, Mapping)
        ),
        abilities=dict(data["abilities"]),
        skill_proficiencies=dict(data["skill_proficiencies"]),
        saving_throw_proficiencies=dict(data["saving_throw_proficiencies"]),
        skill_bonuses=dict(data["skill_bonuses"]),
        saving_throw_bonuses=dict(data["saving_throw_bonuses"]),
        initiative_bonus_value=data["initiative_bonus_value"],
        loadout=CharacterLoadout(
            armor=loadout["armor"],
            shield=loadout["shield"],
            weapons=tuple(loadout["weapons"]),
            two_handed_weapons=tuple(loadout["two_handed_weapons"]),
            armor_class_bonus=loadout["armor_class_bonus"],
            weapon_attack_bonus=loadout["weapon_attack_bonus"],
        ),
        maximum_hit_points=data["maximum_hit_points"],
        current_hit_points=data["current_hit_points"],
        temporary_hit_points=data["temporary_hit_points"],
        notes=tuple(data["notes"]),
    )


def validate_character_sheet_data(data: Mapping[str, Any]) -> ValidationResult:
    """Validate JSON-style character sheet import data without raising."""

    errors: list[ValidationErrorDetail] = []
    _validate_required_keys(data, _CHARACTER_SHEET_KEYS, "$", errors)

    if data.get("type") != "character_sheet":
        errors.append(ValidationErrorDetail("$.type", "must be 'character_sheet'"))
    if data.get("version") != CHARACTER_SHEET_SCHEMA_VERSION:
        errors.append(
            ValidationErrorDetail(
                "$.version",
                f"must be {CHARACTER_SHEET_SCHEMA_VERSION}",
            )
        )

    _expect_type(data, "id", str, "$.id", errors)
    _expect_type(data, "name", str, "$.name", errors)
    _validate_classes(data.get("classes"), errors)
    _expect_string_int_mapping(data.get("abilities"), "$.abilities", errors)
    _expect_string_string_mapping(
        data.get("skill_proficiencies"),
        "$.skill_proficiencies",
        errors,
    )
    _expect_string_string_mapping(
        data.get("saving_throw_proficiencies"),
        "$.saving_throw_proficiencies",
        errors,
    )
    _expect_string_int_mapping(data.get("skill_bonuses"), "$.skill_bonuses", errors)
    _expect_string_int_mapping(data.get("saving_throw_bonuses"), "$.saving_throw_bonuses", errors)
    _expect_type(data, "initiative_bonus_value", int, "$.initiative_bonus_value", errors)
    _validate_loadout(data.get("loadout"), errors)
    _expect_optional_int(data.get("maximum_hit_points"), "$.maximum_hit_points", errors)
    _expect_optional_int(data.get("current_hit_points"), "$.current_hit_points", errors)
    _expect_type(data, "temporary_hit_points", int, "$.temporary_hit_points", errors)
    _expect_string_list(data.get("notes"), "$.notes", errors)

    if errors:
        return ValidationResult(tuple(errors))

    try:
        _character_sheet_from_validated_data(data)
    except ValueError as error:
        return ValidationResult((ValidationErrorDetail("$", str(error)),))
    return ValidationResult()


def load_character_sheet(path: str | Path) -> CharacterSheet:
    """Load a character sheet from a JSON file."""

    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("character sheet file must contain a JSON object")
    return character_sheet_from_data(data)


def dump_character_sheet(sheet: CharacterSheet, path: str | Path, *, indent: int = 2) -> None:
    """Write a character sheet as JSON."""

    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(character_sheet_to_data(sheet), file, indent=indent)
        file.write("\n")


_CHARACTER_SHEET_KEYS = {
    "type",
    "version",
    "id",
    "name",
    "classes",
    "abilities",
    "skill_proficiencies",
    "saving_throw_proficiencies",
    "skill_bonuses",
    "saving_throw_bonuses",
    "initiative_bonus_value",
    "loadout",
    "maximum_hit_points",
    "current_hit_points",
    "temporary_hit_points",
    "notes",
}

_LOADOUT_KEYS = {
    "armor",
    "shield",
    "weapons",
    "two_handed_weapons",
    "armor_class_bonus",
    "weapon_attack_bonus",
}


def _validate_required_keys(
    data: Mapping[str, Any],
    expected: set[str],
    path: str,
    errors: list[ValidationErrorDetail],
) -> None:
    missing = expected - set(data)
    for key in sorted(missing):
        errors.append(ValidationErrorDetail(f"{path}.{key}", "is required"))
    extra = set(data) - expected
    for key in sorted(extra):
        errors.append(ValidationErrorDetail(f"{path}.{key}", "is not supported"))


def _expect_type(
    data: Mapping[str, Any],
    key: str,
    expected_type: type,
    path: str,
    errors: list[ValidationErrorDetail],
) -> None:
    if key in data and not isinstance(data[key], expected_type):
        errors.append(ValidationErrorDetail(path, f"must be {expected_type.__name__}"))


def _validate_classes(value: Any, errors: list[ValidationErrorDetail]) -> None:
    if not isinstance(value, list):
        errors.append(ValidationErrorDetail("$.classes", "must be a list"))
        return
    for index, entry in enumerate(value):
        path = f"$.classes[{index}]"
        if not isinstance(entry, Mapping):
            errors.append(ValidationErrorDetail(path, "must be an object"))
            continue
        _validate_required_keys(entry, {"name", "level"}, path, errors)
        _expect_type(entry, "name", str, f"{path}.name", errors)
        _expect_type(entry, "level", int, f"{path}.level", errors)


def _validate_loadout(value: Any, errors: list[ValidationErrorDetail]) -> None:
    if not isinstance(value, Mapping):
        errors.append(ValidationErrorDetail("$.loadout", "must be an object"))
        return
    _validate_required_keys(value, _LOADOUT_KEYS, "$.loadout", errors)
    _expect_optional_string(value.get("armor"), "$.loadout.armor", errors)
    _expect_optional_string(value.get("shield"), "$.loadout.shield", errors)
    _expect_string_list(value.get("weapons"), "$.loadout.weapons", errors)
    _expect_string_list(
        value.get("two_handed_weapons"),
        "$.loadout.two_handed_weapons",
        errors,
    )
    _expect_mapping_value_type(value, "armor_class_bonus", int, "$.loadout.armor_class_bonus", errors)
    _expect_mapping_value_type(
        value,
        "weapon_attack_bonus",
        int,
        "$.loadout.weapon_attack_bonus",
        errors,
    )


def _expect_mapping_value_type(
    data: Mapping[str, Any],
    key: str,
    expected_type: type,
    path: str,
    errors: list[ValidationErrorDetail],
) -> None:
    if key in data and not isinstance(data[key], expected_type):
        errors.append(ValidationErrorDetail(path, f"must be {expected_type.__name__}"))


def _expect_optional_string(
    value: Any,
    path: str,
    errors: list[ValidationErrorDetail],
) -> None:
    if value is not None and not isinstance(value, str):
        errors.append(ValidationErrorDetail(path, "must be string or null"))


def _expect_optional_int(
    value: Any,
    path: str,
    errors: list[ValidationErrorDetail],
) -> None:
    if value is not None and not isinstance(value, int):
        errors.append(ValidationErrorDetail(path, "must be int or null"))


def _expect_string_list(
    value: Any,
    path: str,
    errors: list[ValidationErrorDetail],
) -> None:
    if not isinstance(value, list):
        errors.append(ValidationErrorDetail(path, "must be a list"))
        return
    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(ValidationErrorDetail(f"{path}[{index}]", "must be string"))


def _expect_string_string_mapping(
    value: Any,
    path: str,
    errors: list[ValidationErrorDetail],
) -> None:
    if not isinstance(value, Mapping):
        errors.append(ValidationErrorDetail(path, "must be an object"))
        return
    for key, item in value.items():
        if not isinstance(key, str):
            errors.append(ValidationErrorDetail(path, "keys must be strings"))
        if not isinstance(item, str):
            errors.append(ValidationErrorDetail(f"{path}.{key}", "must be string"))


def _expect_string_int_mapping(
    value: Any,
    path: str,
    errors: list[ValidationErrorDetail],
) -> None:
    if not isinstance(value, Mapping):
        errors.append(ValidationErrorDetail(path, "must be an object"))
        return
    for key, item in value.items():
        if not isinstance(key, str):
            errors.append(ValidationErrorDetail(path, "keys must be strings"))
        if not isinstance(item, int):
            errors.append(ValidationErrorDetail(f"{path}.{key}", "must be int"))
