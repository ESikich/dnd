from typing import cast

import pytest

from dnd5e import (
    Ability,
    CharacterClassLevel,
    CharacterLoadout,
    CharacterSheet,
    ProficiencyLevel,
    Skill,
    character_sheet_armor_class,
    character_sheet_combatant,
    character_sheet_hit_points,
    character_sheet_initiative_bonus,
    character_sheet_level,
    character_sheet_max_hit_points,
    character_sheet_passive_skill,
    character_sheet_saving_throw_bonus,
    character_sheet_skill_bonus,
    character_sheet_spell_attack_bonus,
    character_sheet_spell_save_dc,
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
    assert character_sheet_spell_attack_bonus(sheet, "int") == 3
    assert character_sheet_spell_save_dc(sheet, "int") == 11
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


def test_character_sheet_validates_proficiency_choices() -> None:
    with pytest.raises(ValueError, match="unknown skill proficiency: tactics"):
        CharacterSheet(
            id="bad-skill",
            name="Bad Skill",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities=abilities(),
            skill_proficiencies=cast(dict[Skill, ProficiencyLevel], {"tactics": "proficient"}),
        )

    with pytest.raises(ValueError, match="unknown skill proficiency for stealth: trained"):
        CharacterSheet(
            id="bad-proficiency",
            name="Bad Proficiency",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities=abilities(),
            skill_proficiencies=cast(dict[Skill, ProficiencyLevel], {"stealth": "trained"}),
        )

    with pytest.raises(ValueError, match="unknown saving throw proficiency: luck"):
        CharacterSheet(
            id="bad-save",
            name="Bad Save",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities=abilities(),
            saving_throw_proficiencies=cast(
                dict[Ability, ProficiencyLevel],
                {"luck": "proficient"},
            ),
        )


def test_character_sheet_validates_bonus_keys() -> None:
    with pytest.raises(ValueError, match="unknown skill bonus: tactics"):
        CharacterSheet(
            id="bad-skill-bonus",
            name="Bad Skill Bonus",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities=abilities(),
            skill_bonuses=cast(dict[Skill, int], {"tactics": 1}),
        )

    with pytest.raises(ValueError, match="unknown saving throw bonus: luck"):
        CharacterSheet(
            id="bad-save-bonus",
            name="Bad Save Bonus",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities=abilities(),
            saving_throw_bonuses=cast(dict[Ability, int], {"luck": 1}),
        )


def test_character_sheet_validates_loadout_ids() -> None:
    with pytest.raises(ValueError, match="unknown armor: enchanted_pajamas"):
        CharacterSheet(
            id="bad-armor",
            name="Bad Armor",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities=abilities(),
            loadout=CharacterLoadout(armor="enchanted_pajamas"),
        )

    with pytest.raises(ValueError, match="unknown shield: buckler"):
        CharacterSheet(
            id="bad-shield",
            name="Bad Shield",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities=abilities(),
            loadout=CharacterLoadout(shield="buckler"),
        )

    with pytest.raises(ValueError, match="unknown weapon: spoon"):
        CharacterSheet(
            id="bad-weapon",
            name="Bad Weapon",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities=abilities(),
            loadout=CharacterLoadout(weapons=("spoon",)),
        )

    with pytest.raises(ValueError, match="two-handed weapon is not equipped: longsword"):
        CharacterSheet(
            id="bad-two-handed",
            name="Bad Two-Handed",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities=abilities(),
            loadout=CharacterLoadout(weapons=("shortbow",), two_handed_weapons=("longsword",)),
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
