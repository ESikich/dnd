import pytest

from dnd5e import (
    CharacterClassLevel,
    CharacterSheet,
    CharacterSpellcastingProgression,
    character_sheet_class_features,
    character_sheet_class_progression,
    character_sheet_spellcasting_progression,
)


def test_character_sheet_class_progression_returns_granted_features_and_table_values() -> None:
    sheet = character("fighter", 5)

    progression = character_sheet_class_progression(sheet)

    assert tuple(feature.id for feature in progression.features) == (
        "fighter_fighting_style",
        "second_wind",
        "action_surge_1_use",
        "martial_archetype",
        "fighter_ability_score_improvement_1",
        "extra_attack_1",
    )
    assert progression.class_specific == {
        "action_surges": 1,
        "indomitable_uses": 0,
        "extra_attacks": 1,
    }
    assert progression.ability_score_bonuses == 2
    assert progression.spellcasting is None


def test_character_sheet_class_features_supports_subclass_progression() -> None:
    sheet = character("fighter", 3)

    features = character_sheet_class_features(sheet, subclasses={"fighter": "champion"})

    assert tuple(feature.id for feature in features) == (
        "fighter_fighting_style",
        "second_wind",
        "action_surge_1_use",
        "martial_archetype",
        "improved_critical",
    )


def test_character_sheet_class_features_rejects_wrong_subclass_class() -> None:
    sheet = character("fighter", 3)

    with pytest.raises(ValueError, match="subclass does not belong to class"):
        character_sheet_class_progression(sheet, subclasses={"fighter": "evocation"})


def test_character_sheet_spellcasting_progression_projects_slots() -> None:
    sheet = character("wizard", 5)

    spellcasting = character_sheet_spellcasting_progression(sheet)

    assert isinstance(spellcasting, CharacterSpellcastingProgression)
    assert spellcasting.cantrips_known == 4
    assert spellcasting.spells_known is None
    assert spellcasting.spell_slots == {1: 4, 2: 3, 3: 2}


def test_character_sheet_spellcasting_progression_returns_none_for_non_caster() -> None:
    assert character_sheet_spellcasting_progression(character("fighter", 5)) is None


def character(class_name: str, level: int) -> CharacterSheet:
    return CharacterSheet(
        id="hero",
        name="Hero",
        classes=(CharacterClassLevel(class_name, level),),  # type: ignore[arg-type]
        abilities={
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
        },
    )
