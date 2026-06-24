import pytest

from dnd5e import (
    SPELLS,
    SPELL_COMPONENTS,
    SPELL_SCHOOLS,
    CharacterRules,
    SpellDefinition,
    spell_attack_bonus,
    spell_save_dc,
)


def test_public_spell_imports_and_docstrings() -> None:
    assert "evocation" in SPELL_SCHOOLS
    assert "verbal" in SPELL_COMPONENTS
    assert SpellDefinition.__doc__
    assert isinstance(SPELLS["fire_bolt"], SpellDefinition)


def test_spell_catalog_includes_basic_srd_style_metadata() -> None:
    fire_bolt = SPELLS["fire_bolt"]
    detect_magic = SPELLS["detect_magic"]
    mage_armor = SPELLS["mage_armor"]

    assert fire_bolt.level == 0
    assert fire_bolt.school == "evocation"
    assert fire_bolt.range == "120 feet"
    assert fire_bolt.components == ("verbal", "somatic")
    assert detect_magic.concentration is True
    assert detect_magic.ritual is True
    assert mage_armor.material == "cured leather"


def test_spell_definition_rejects_invalid_core_metadata() -> None:
    with pytest.raises(ValueError, match="spell id is required"):
        SpellDefinition("", "Test", 1, "evocation", "1 action", "self", "instantaneous", ("verbal",))

    with pytest.raises(ValueError, match="spell level"):
        SpellDefinition("test", "Test", 10, "evocation", "1 action", "self", "instantaneous", ("verbal",))

    with pytest.raises(ValueError, match="unknown spell school"):
        SpellDefinition("test", "Test", 1, "dunamancy", "1 action", "self", "instantaneous", ("verbal",))

    with pytest.raises(ValueError, match="casting_time is required"):
        SpellDefinition("test", "Test", 1, "evocation", "", "self", "instantaneous", ("verbal",))


def test_spell_definition_rejects_invalid_components() -> None:
    with pytest.raises(ValueError, match="components are required"):
        SpellDefinition("test", "Test", 1, "evocation", "1 action", "self", "instantaneous", ())

    with pytest.raises(ValueError, match="unknown spell component"):
        SpellDefinition("test", "Test", 1, "evocation", "1 action", "self", "instantaneous", ("focus",))

    with pytest.raises(ValueError, match="requires a material component"):
        SpellDefinition(
            "test",
            "Test",
            1,
            "evocation",
            "1 action",
            "self",
            "instantaneous",
            ("verbal",),
            material="a tiny bell",
        )


def test_spellcasting_helpers_use_ability_and_proficiency() -> None:
    caster = CharacterRules(
        level=5,
        abilities={
            "str": 8,
            "dex": 14,
            "con": 12,
            "int": 16,
            "wis": 10,
            "cha": 13,
        },
    )

    assert spell_attack_bonus(caster, "int") == 6
    assert spell_save_dc(caster, "int") == 14


def test_spellcasting_helpers_accept_flat_bonuses() -> None:
    caster = CharacterRules(
        level=1,
        abilities={
            "str": 8,
            "dex": 10,
            "con": 12,
            "int": 14,
            "wis": 16,
            "cha": 10,
        },
    )

    assert spell_attack_bonus(caster, "wis", bonus=1) == 6
    assert spell_save_dc(caster, "wis", bonus=1) == 14
