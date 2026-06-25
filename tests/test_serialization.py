from pathlib import Path

import pytest

from dnd5e import (
    CHARACTER_SHEET_SCHEMA_VERSION,
    CharacterClassLevel,
    CharacterLoadout,
    CharacterSheet,
    ValidationErrorDetail,
    ValidationResult,
    character_sheet_from_data,
    character_sheet_to_data,
    dump_character_sheet,
    load_character_sheet,
    validate_character_sheet_data,
)


def test_public_serialization_imports_and_docstrings() -> None:
    assert CHARACTER_SHEET_SCHEMA_VERSION == 1
    assert ValidationErrorDetail.__doc__
    assert ValidationResult.__doc__


def test_character_sheet_round_trips_through_json_compatible_data() -> None:
    sheet = sample_sheet()

    data = character_sheet_to_data(sheet)
    restored = character_sheet_from_data(data)

    assert data["type"] == "character_sheet"
    assert data["version"] == 1
    assert data["classes"] == [{"name": "fighter", "level": 5}]
    assert data["loadout"]["weapons"] == ["longsword", "shortbow"]
    assert data["loadout"]["magic_items"] == ["ring_of_protection"]
    assert data["loadout"]["attuned_magic_items"] == ["ring_of_protection"]
    assert restored == sheet


def test_character_sheet_from_data_accepts_legacy_loadout_without_magic_items() -> None:
    data = character_sheet_to_data(sample_sheet())
    del data["loadout"]["magic_items"]
    del data["loadout"]["attuned_magic_items"]

    restored = character_sheet_from_data(data)

    assert restored.loadout.magic_items == ()
    assert restored.loadout.attuned_magic_items == ()


def test_character_sheet_round_trips_through_json_file(tmp_path: Path) -> None:
    sheet = sample_sheet()
    path = tmp_path / "kara.json"

    dump_character_sheet(sheet, path)
    restored = load_character_sheet(path)

    assert restored == sheet
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_character_sheet_validation_reports_shape_and_domain_errors() -> None:
    data = character_sheet_to_data(sample_sheet())
    data["version"] = 999
    data["classes"] = [{"name": "fighter", "level": "five"}]
    data["loadout"] = {**data["loadout"], "weapons": ["longsword", 42]}

    result = validate_character_sheet_data(data)

    assert result.valid is False
    assert ("$.version", "must be 1") in error_pairs(result)
    assert ("$.classes[0].level", "must be int") in error_pairs(result)
    assert ("$.loadout.weapons[1]", "must be string") in error_pairs(result)

    domain_data = character_sheet_to_data(sample_sheet())
    domain_data["abilities"] = {**domain_data["abilities"], "str": 99}

    domain_result = validate_character_sheet_data(domain_data)

    assert domain_result.valid is False
    assert domain_result.errors[0].path == "$"
    assert "str score" in domain_result.errors[0].message


def test_character_sheet_from_data_raises_first_validation_error() -> None:
    data = character_sheet_to_data(sample_sheet())
    del data["name"]

    with pytest.raises(ValueError, match=r"\$\.name: is required"):
        character_sheet_from_data(data)


def sample_sheet() -> CharacterSheet:
    return CharacterSheet(
        id="kara",
        name="Kara",
        classes=(CharacterClassLevel("fighter", 5),),
        abilities={
            "str": 16,
            "dex": 14,
            "con": 14,
            "int": 10,
            "wis": 12,
            "cha": 8,
        },
        skill_proficiencies={"athletics": "expertise", "perception": "proficient"},
        saving_throw_proficiencies={"str": "proficient", "con": "proficient"},
        skill_bonuses={"perception": 1},
        initiative_bonus_value=1,
        loadout=CharacterLoadout(
            armor="chain_mail",
            shield="shield",
            weapons=("longsword", "shortbow"),
            two_handed_weapons=("longsword",),
            magic_items=("ring_of_protection",),
            attuned_magic_items=("ring_of_protection",),
        ),
        current_hit_points=28,
        temporary_hit_points=3,
        notes=("keeps watch",),
    )


def error_pairs(result: ValidationResult) -> set[tuple[str, str]]:
    return {(error.path, error.message) for error in result.errors}
