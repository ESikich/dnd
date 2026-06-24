import pytest

from dnd5e import (
    CharacterClassLevel,
    CharacterLoadout,
    CharacterSheet,
    character_sheet_armor_class,
    character_sheet_combatant,
    character_sheet_hit_points,
    character_sheet_initiative_bonus,
    character_sheet_level,
    character_sheet_max_hit_points,
    character_sheet_passive_skill,
    character_sheet_saving_throw_bonus,
    character_sheet_skill_bonus,
    character_sheet_weapon_profile,
    character_sheet_weapon_profiles,
)


def test_character_sheet_derives_core_stats_from_rules_and_loadout() -> None:
    sheet = fighter_sheet()

    assert character_sheet_level(sheet) == 5
    assert character_sheet_initiative_bonus(sheet) == 3
    assert character_sheet_skill_bonus(sheet, "athletics") == 9
    assert character_sheet_passive_skill(sheet, "perception") == 15
    assert character_sheet_saving_throw_bonus(sheet, "con") == 5
    assert character_sheet_armor_class(sheet).total == 18

    hp = character_sheet_hit_points(sheet)
    assert character_sheet_max_hit_points(sheet) == 44
    assert hp.current == 28
    assert hp.maximum == 44


def test_character_sheet_weapon_profiles_use_loadout_and_training() -> None:
    sheet = fighter_sheet()

    longsword = character_sheet_weapon_profile(sheet, "longsword")
    profiles = character_sheet_weapon_profiles(sheet)

    assert longsword.proficient
    assert longsword.attack_bonus == 6
    assert longsword.damage_dice == "1d10"
    assert tuple(profile.weapon.id for profile in profiles) == ("longsword", "shortbow")


def test_character_sheet_combatant_uses_derived_ac_hp_and_initiative() -> None:
    sheet = fighter_sheet()

    combatant = character_sheet_combatant(sheet, roll=12, conditions=("poisoned",))

    assert combatant.id == "kara"
    assert combatant.name == "Kara"
    assert combatant.initiative == 15
    assert combatant.armor_class == 18
    assert combatant.hit_points.current == 28
    assert combatant.source is sheet


def test_character_sheet_validates_missing_abilities() -> None:
    with pytest.raises(ValueError, match="missing ability scores"):
        CharacterSheet(
            id="bad",
            name="Bad Sheet",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities={
                "str": 10,
                "dex": 10,
                "con": 10,
                "int": 10,
                "wis": 10,
            },
        )


def test_character_sheet_validates_total_level() -> None:
    with pytest.raises(ValueError, match="total character level"):
        CharacterSheet(
            id="too-high",
            name="Too High",
            classes=(CharacterClassLevel("fighter", 20), CharacterClassLevel("rogue", 1)),
            abilities=abilities(),
        )


def fighter_sheet() -> CharacterSheet:
    return CharacterSheet(
        id="kara",
        name="Kara",
        classes=(CharacterClassLevel("fighter", 5),),
        abilities=abilities(strength=16, dexterity=14, constitution=14, wisdom=12, charisma=8),
        skill_proficiencies={
            "athletics": "expertise",
            "perception": "proficient",
        },
        saving_throw_proficiencies={
            "str": "proficient",
            "con": "proficient",
        },
        skill_bonuses={"perception": 1},
        initiative_bonus_value=1,
        loadout=CharacterLoadout(
            armor="chain_mail",
            shield="shield",
            weapons=("longsword", "shortbow"),
            two_handed_weapons=("longsword",),
        ),
        current_hit_points=28,
    )


def abilities(
    *,
    strength: int = 10,
    dexterity: int = 10,
    constitution: int = 10,
    intelligence: int = 10,
    wisdom: int = 10,
    charisma: int = 10,
) -> dict:
    return {
        "str": strength,
        "dex": dexterity,
        "con": constitution,
        "int": intelligence,
        "wis": wisdom,
        "cha": charisma,
    }
