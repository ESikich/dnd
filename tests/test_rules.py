from pathlib import Path
from typing import cast

import pytest

from dnd5e import (
    Ability,
    CONDITIONS,
    SRD_CLASSES,
    ArmorTraining,
    CharacterClassName,
    ClassDefinition,
    ClassPack,
    ConditionDefinition,
    ConditionPack,
    CharacterRules,
    ConditionName,
    ConditionTag,
    ProficiencyLevel,
    Skill,
    WeaponTraining,
    ability_modifier,
    attack_roll,
    average_dice,
    create_combat,
    d20_check,
    damage_roll,
    initiative_bonus,
    load_builtin_class_pack,
    load_builtin_condition_pack,
    load_class_pack,
    load_class_pack_data,
    load_condition_pack,
    load_condition_pack_data,
    passive_skill,
    parse_dice_notation,
    proficiency_bonus,
    roll_dice,
    saving_throw_bonus,
    skill_bonus,
)


def test_ability_modifiers() -> None:
    assert ability_modifier(1) == -5
    assert ability_modifier(10) == 0
    assert ability_modifier(18) == 4


def test_proficiency_by_level() -> None:
    assert proficiency_bonus(1) == 2
    assert proficiency_bonus(5) == 3
    assert proficiency_bonus(9) == 4
    assert proficiency_bonus(13) == 5
    assert proficiency_bonus(17) == 6


def test_d20_check() -> None:
    result = d20_check(
        ability_score=16,
        proficiency_bonus_value=2,
        proficiency="proficient",
        roll=12,
    )

    assert result.total == 17


def test_dice() -> None:
    result = roll_dice("2d6+3", rng=lambda: 0)

    assert result.rolls == (1, 1)
    assert result.total == 5
    assert average_dice("2d6+3") == 10


def test_dice_notation_validation() -> None:
    with pytest.raises(ValueError, match="invalid dice notation"):
        parse_dice_notation("2dd6")

    with pytest.raises(ValueError, match="dice count must be positive"):
        parse_dice_notation("0d6")

    with pytest.raises(ValueError, match="dice sides must be at least 2"):
        parse_dice_notation("1d1")


def test_d20_input_validation() -> None:
    with pytest.raises(ValueError, match="roll must be from 1 to 20"):
        d20_check(ability_score=10, roll=21)

    with pytest.raises(ValueError, match="level must be from 1 to 20"):
        proficiency_bonus(21)


def test_character_helpers() -> None:
    character = CharacterRules(
        level=5,
        abilities={
            "str": 8,
            "dex": 16,
            "con": 14,
            "int": 10,
            "wis": 12,
            "cha": 10,
        },
        skill_proficiencies={"stealth": "expertise", "perception": "proficient"},
        saving_throw_proficiencies={"dex": "proficient"},
        initiative_bonus_value=1,
    )

    assert skill_bonus(character, "stealth") == 9
    assert passive_skill(character, "perception") == 14
    assert saving_throw_bonus(character, "dex") == 6
    assert initiative_bonus(character) == 4


def test_character_rules_validates_core_inputs() -> None:
    with pytest.raises(ValueError, match="level must be from 1 to 20"):
        CharacterRules(level=0, abilities=abilities())

    with pytest.raises(ValueError, match="missing ability scores"):
        CharacterRules(
            level=1,
            abilities={
                "str": 10,
                "dex": 10,
                "con": 10,
                "int": 10,
                "wis": 10,
            },
        )

    with pytest.raises(ValueError, match="cha score must be from 1 to 30"):
        CharacterRules(level=1, abilities=abilities(charisma=31))

    with pytest.raises(ValueError, match="unknown skill proficiency: tactics"):
        CharacterRules(
            level=1,
            abilities=abilities(),
            skill_proficiencies=cast(dict[Skill, ProficiencyLevel], {"tactics": "proficient"}),
        )

    with pytest.raises(ValueError, match="unknown skill proficiency for stealth: trained"):
        CharacterRules(
            level=1,
            abilities=abilities(),
            skill_proficiencies=cast(dict[Skill, ProficiencyLevel], {"stealth": "trained"}),
        )

    with pytest.raises(ValueError, match="unknown saving throw bonus: luck"):
        CharacterRules(
            level=1,
            abilities=abilities(),
            saving_throw_bonuses=cast(dict[Ability, int], {"luck": 1}),
        )


def test_combat() -> None:
    combat = create_combat(
        [
            {"id": "a", "name": "Aria", "initiative_bonus": 2, "roll": 10},
            {"id": "b", "name": "Borin", "initiative_bonus": 1, "roll": 18},
        ]
    )

    assert combat.current.id == "b"


def test_attack_rolls() -> None:
    assert attack_roll(attacker_bonus=5, target_armor_class=15, roll=1).outcome == "critical-miss"
    assert attack_roll(attacker_bonus=5, target_armor_class=99, roll=20).outcome == "critical-hit"
    assert attack_roll(attacker_bonus=5, target_armor_class=15, roll=10).outcome == "hit"


def test_critical_damage_doubles_dice() -> None:
    result = damage_roll(dice="1d8+3", type="slashing", critical=True, rng=lambda: 0)

    assert result.rolls[0].notation == "2d8+3"
    assert result.total == 5


def test_class_metadata() -> None:
    assert SRD_CLASSES["fighter"].hit_die == 10
    assert SRD_CLASSES["wizard"].saving_throws == ("int", "wis")
    assert isinstance(load_builtin_class_pack(), ClassPack)
    assert load_builtin_class_pack().classes["fighter"] == SRD_CLASSES["fighter"]


def test_class_pack_data_loads_user_content() -> None:
    pack = load_class_pack_data(
        {
            "classes": [
                {
                    "name": "fighter",
                    "hit_die": 10,
                    "primary_abilities": ["str"],
                    "saving_throws": ["str", "con"],
                    "armor_training": ["light"],
                    "weapon_training": ["simple"],
                    "skill_choices": ["athletics"],
                    "skill_choice_count": 1,
                }
            ]
        }
    )

    assert pack.classes["fighter"].primary_abilities == ("str",)
    assert pack.classes["fighter"].skill_choices == ("athletics",)


def test_class_pack_loads_json_file(tmp_path: Path) -> None:
    path = tmp_path / "classes.json"
    path.write_text(
        """
        {
          "classes": [
            {
              "name": "wizard",
              "hit_die": 6,
              "primary_abilities": ["int"],
              "saving_throws": ["int", "wis"],
              "armor_training": [],
              "weapon_training": ["simple"],
              "skill_choices": ["arcana", "history"],
              "skill_choice_count": 1
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    pack = load_class_pack(path)

    assert pack.classes["wizard"].hit_die == 6


def test_class_pack_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="missing sections"):
        load_class_pack_data({})

    with pytest.raises(ValueError, match="unknown sections"):
        load_class_pack_data({"classes": [], "subclasses": []})

    with pytest.raises(ValueError, match="unknown fields"):
        load_class_pack_data(
            {
                "classes": [
                    {
                        "name": "fighter",
                        "hit_die": 10,
                        "primary_abilities": ["str"],
                        "saving_throws": ["str", "con"],
                        "armor_training": ["light"],
                        "weapon_training": ["simple"],
                        "skill_choices": ["athletics"],
                        "skill_choice_count": 1,
                        "spellcasting": False,
                    }
                ]
            }
        )

    with pytest.raises(ValueError, match="duplicate class name"):
        load_class_pack_data(
            {
                "classes": [
                    {
                        "name": "fighter",
                        "hit_die": 10,
                        "primary_abilities": ["str"],
                        "saving_throws": ["str", "con"],
                        "armor_training": ["light"],
                        "weapon_training": ["simple"],
                        "skill_choices": ["athletics"],
                        "skill_choice_count": 1,
                    },
                    {
                        "name": "fighter",
                        "hit_die": 10,
                        "primary_abilities": ["dex"],
                        "saving_throws": ["str", "con"],
                        "armor_training": ["light"],
                        "weapon_training": ["simple"],
                        "skill_choices": ["acrobatics"],
                        "skill_choice_count": 1,
                    },
                ]
            }
        )


def test_class_metadata_validates_impossible_values() -> None:
    with pytest.raises(ValueError, match="unknown class: artificer"):
        ClassDefinition(
            cast(CharacterClassName, "artificer"),
            8,
            ("int",),
            ("int", "con"),
            ("light",),
            ("simple",),
            ("arcana",),
            1,
        )

    with pytest.raises(ValueError, match="class hit die must be one of"):
        ClassDefinition("fighter", 7, ("str",), ("str", "con"), ("light",), ("simple",), ("athletics",), 1)

    with pytest.raises(ValueError, match="unknown primary ability: luck"):
        ClassDefinition(
            "fighter",
            10,
            cast(tuple[Ability, ...], ("luck",)),
            ("str", "con"),
            ("light",),
            ("simple",),
            ("athletics",),
            1,
        )

    with pytest.raises(ValueError, match="unknown armor training: cloth"):
        ClassDefinition(
            "fighter",
            10,
            ("str",),
            ("str", "con"),
            cast(tuple[ArmorTraining, ...], ("cloth",)),
            ("simple",),
            ("athletics",),
            1,
        )

    with pytest.raises(ValueError, match="unknown weapon training: exotic"):
        ClassDefinition(
            "fighter",
            10,
            ("str",),
            ("str", "con"),
            ("light",),
            cast(tuple[WeaponTraining, ...], ("exotic",)),
            ("athletics",),
            1,
        )

    with pytest.raises(ValueError, match="unknown skill choice: tactics"):
        ClassDefinition(
            "fighter",
            10,
            ("str",),
            ("str", "con"),
            ("light",),
            ("simple",),
            cast(tuple[Skill, ...], ("tactics",)),
            1,
        )

    with pytest.raises(ValueError, match="skill choice count cannot exceed available skill choices"):
        ClassDefinition("fighter", 10, ("str",), ("str", "con"), ("light",), ("simple",), ("athletics",), 2)


def test_condition_metadata() -> None:
    assert CONDITIONS["poisoned"].tags == ("attack_rolls_affected", "ability_checks_affected")
    assert "cannot_act" in CONDITIONS["unconscious"].tags
    assert isinstance(load_builtin_condition_pack(), ConditionPack)
    assert load_builtin_condition_pack().conditions["poisoned"] == CONDITIONS["poisoned"]


def test_condition_pack_data_loads_user_content() -> None:
    pack = load_condition_pack_data(
        {
            "conditions": [
                {
                    "name": "poisoned",
                    "tags": ["attack_rolls_affected", "ability_checks_affected"],
                }
            ]
        }
    )

    assert pack.conditions["poisoned"].tags == (
        "attack_rolls_affected",
        "ability_checks_affected",
    )


def test_condition_pack_loads_json_file(tmp_path: Path) -> None:
    path = tmp_path / "conditions.json"
    path.write_text(
        """
        {
          "conditions": [
            {
              "name": "grappled",
              "tags": ["speed_zero"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    pack = load_condition_pack(path)

    assert pack.conditions["grappled"].tags == ("speed_zero",)


def test_condition_pack_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="missing sections"):
        load_condition_pack_data({})

    with pytest.raises(ValueError, match="unknown sections"):
        load_condition_pack_data({"conditions": [], "diseases": []})

    with pytest.raises(ValueError, match="content section conditions must be a list"):
        load_condition_pack_data({"conditions": {}})

    with pytest.raises(ValueError, match="entries must be objects"):
        load_condition_pack_data({"conditions": ["poisoned"]})

    with pytest.raises(ValueError, match="unknown fields"):
        load_condition_pack_data(
            {
                "conditions": [
                    {
                        "name": "poisoned",
                        "tags": ["attack_rolls_affected"],
                        "description": "",
                    }
                ]
            }
        )

    with pytest.raises(ValueError, match="duplicate condition name"):
        load_condition_pack_data(
            {
                "conditions": [
                    {"name": "poisoned", "tags": ["attack_rolls_affected"]},
                    {"name": "poisoned", "tags": ["ability_checks_affected"]},
                ]
            }
        )


def test_condition_metadata_validates_impossible_values() -> None:
    with pytest.raises(ValueError, match="unknown condition: burning"):
        ConditionDefinition(cast(ConditionName, "burning"), ("cannot_act",))

    with pytest.raises(ValueError, match="unknown condition tag: on_fire"):
        ConditionDefinition("poisoned", cast(tuple[ConditionTag, ...], ("on_fire",)))


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
