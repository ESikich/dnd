from pathlib import Path
from typing import cast

import pytest

from dnd5e import (
    ARMOR,
    SHIELDS,
    WEAPONS,
    ArmorCategory,
    ArmorClassResult,
    ArmorDefinition,
    CharacterRules,
    DamageType,
    ShieldDefinition,
    WeaponAttackProfile,
    WeaponCategory,
    WeaponDefinition,
    WeaponProperty,
    WeaponRangeType,
    armor_class,
    load_builtin_equipment_pack,
    load_equipment_pack,
    load_equipment_pack_data,
    weapon_attack_bonus,
    weapon_attack_profile,
    weapon_damage_bonus,
    weapon_damage_dice,
)


def test_public_equipment_imports() -> None:
    assert isinstance(ARMOR["leather"], ArmorDefinition)
    assert isinstance(SHIELDS["shield"], ShieldDefinition)
    assert isinstance(WEAPONS["rapier"], WeaponDefinition)
    assert ArmorClassResult is not None
    assert WeaponAttackProfile is not None


def test_unarmored_ac_uses_dexterity_modifier() -> None:
    character = character_with(strength=10, dexterity=16)

    result = armor_class(character)

    assert result.total == 13
    assert result.base == 10
    assert result.dexterity_bonus == 3


def test_light_armor_uses_full_dexterity_modifier() -> None:
    character = character_with(strength=10, dexterity=18)

    result = armor_class(character, armor="leather")

    assert result.total == 15
    assert result.base == 11
    assert result.dexterity_bonus == 4


def test_medium_armor_caps_dexterity_modifier_at_two() -> None:
    character = character_with(strength=10, dexterity=18)

    result = armor_class(character, armor="scale_mail")

    assert result.total == 16
    assert result.base == 14
    assert result.dexterity_bonus == 2


def test_heavy_armor_ignores_dexterity_modifier() -> None:
    character = character_with(strength=10, dexterity=18)

    result = armor_class(character, armor="chain_mail")

    assert result.total == 16
    assert result.base == 16
    assert result.dexterity_bonus == 0


def test_shield_adds_ac_bonus() -> None:
    character = character_with(strength=10, dexterity=14)

    result = armor_class(character, armor="leather", shield="shield")

    assert result.total == 15
    assert result.shield_bonus == 2


def test_rapier_chooses_dexterity_for_dexterity_forward_character() -> None:
    character = character_with(strength=10, dexterity=18, level=5)

    profile = weapon_attack_profile(character, "rapier")

    assert profile.ability == "dex"
    assert profile.attack_bonus == 7
    assert profile.damage_bonus == 4
    assert profile.damage_dice == "1d8"


def test_longsword_uses_versatile_damage_when_two_handed() -> None:
    assert weapon_damage_dice("longsword") == "1d8"
    assert weapon_damage_dice("longsword", two_handed=True) == "1d10"


def test_shortbow_uses_dexterity_and_proficiency() -> None:
    character = character_with(strength=16, dexterity=14, level=5)

    profile = weapon_attack_profile(character, "shortbow")

    assert profile.ability == "dex"
    assert profile.attack_bonus == 5
    assert profile.damage_bonus == 2
    assert profile.damage_dice == "1d6"


def test_weapon_helpers_accept_proficiency_and_bonus_overrides() -> None:
    character = character_with(strength=16, dexterity=10, level=5)

    assert weapon_attack_bonus(character, "longsword") == 6
    assert weapon_attack_bonus(character, "longsword", proficient=False) == 3
    assert weapon_attack_bonus(character, "longsword", bonuses=1) == 7
    assert weapon_damage_bonus(character, "longsword", bonuses=2) == 5


def test_armor_definition_validates_impossible_values() -> None:
    with pytest.raises(ValueError, match="armor id is required"):
        ArmorDefinition("", "Nameless", "light", 11, 0, 1)

    with pytest.raises(ValueError, match="unknown armor category"):
        ArmorDefinition("robes", "Robes", cast(ArmorCategory, "cloth"), 10, 0, 1)

    with pytest.raises(ValueError, match="armor base AC must be positive"):
        ArmorDefinition("robes", "Robes", "light", 0, 0, 1)

    with pytest.raises(ValueError, match="armor cost cannot be negative"):
        ArmorDefinition("robes", "Robes", "light", 10, -1, 1)

    with pytest.raises(ValueError, match="armor strength requirement must be from 1 to 30"):
        ArmorDefinition("robes", "Robes", "light", 10, 0, 1, strength_requirement=31)


def test_shield_definition_validates_impossible_values() -> None:
    with pytest.raises(ValueError, match="shield name is required"):
        ShieldDefinition("buckler", "", 1, 0, 1)

    with pytest.raises(ValueError, match="shield AC bonus must be positive"):
        ShieldDefinition("buckler", "Buckler", 0, 0, 1)

    with pytest.raises(ValueError, match="shield weight cannot be negative"):
        ShieldDefinition("buckler", "Buckler", 1, 0, -1)


def test_weapon_definition_validates_impossible_values() -> None:
    with pytest.raises(ValueError, match="unknown weapon category"):
        WeaponDefinition(
            "knife",
            "Knife",
            cast(WeaponCategory, "tiny"),
            "melee",
            "1d4",
            "piercing",
            0,
            1,
        )

    with pytest.raises(ValueError, match="unknown weapon range type"):
        WeaponDefinition(
            "knife",
            "Knife",
            "simple",
            cast(WeaponRangeType, "near"),
            "1d4",
            "piercing",
            0,
            1,
        )

    with pytest.raises(ValueError, match="invalid dice notation"):
        WeaponDefinition("knife", "Knife", "simple", "melee", "bad", "piercing", 0, 1)

    with pytest.raises(ValueError, match="weapon damage dice cannot be negative"):
        WeaponDefinition("knife", "Knife", "simple", "melee", "-1", "piercing", 0, 1)

    with pytest.raises(ValueError, match="unknown weapon damage type"):
        WeaponDefinition(
            "knife",
            "Knife",
            "simple",
            "melee",
            "1d4",
            cast(DamageType, "sharp"),
            0,
            1,
        )

    with pytest.raises(ValueError, match="unknown weapon property"):
        WeaponDefinition(
            "knife",
            "Knife",
            "simple",
            "melee",
            "1d4",
            "piercing",
            0,
            1,
            cast(tuple[WeaponProperty, ...], ("tiny",)),
        )

    with pytest.raises(ValueError, match="versatile damage dice require the versatile property"):
        WeaponDefinition(
            "knife",
            "Knife",
            "simple",
            "melee",
            "1d4",
            "piercing",
            0,
            1,
            versatile_damage_dice="1d6",
        )

    with pytest.raises(ValueError, match="weapon ranges must include both normal and long range"):
        WeaponDefinition("knife", "Knife", "simple", "melee", "1d4", "piercing", 0, 1, normal_range=20)

    with pytest.raises(ValueError, match="weapon long range must be at least normal range"):
        WeaponDefinition("knife", "Knife", "simple", "melee", "1d4", "piercing", 0, 1, normal_range=20, long_range=10)


def test_weapon_definition_allows_flat_non_negative_damage() -> None:
    weapon = WeaponDefinition("net", "Net", "martial", "ranged", "0", "bludgeoning", 100, 3, normal_range=5, long_range=15)

    assert weapon.damage_dice == "0"


def test_builtin_equipment_loads_from_packaged_content() -> None:
    pack = load_builtin_equipment_pack()

    assert pack.armor["chain_mail"] == ARMOR["chain_mail"]
    assert pack.shields["shield"] == SHIELDS["shield"]
    assert pack.weapons["longsword"] == WEAPONS["longsword"]


def test_equipment_pack_data_loads_user_content() -> None:
    pack = load_equipment_pack_data(
        {
            "armor": [
                {
                    "id": "training_leather",
                    "name": "Training Leather",
                    "category": "light",
                    "base_ac": 11,
                    "cost_cp": 0,
                    "weight_lb": 8,
                    "max_dex_bonus": None,
                    "strength_requirement": None,
                    "stealth_disadvantage": False,
                }
            ],
            "shields": [
                {
                    "id": "practice_shield",
                    "name": "Practice Shield",
                    "ac_bonus": 1,
                    "cost_cp": 0,
                    "weight_lb": 3,
                }
            ],
            "weapons": [
                {
                    "id": "practice_sword",
                    "name": "Practice Sword",
                    "category": "simple",
                    "range_type": "melee",
                    "damage_dice": "1d4",
                    "damage_type": "bludgeoning",
                    "cost_cp": 0,
                    "weight_lb": 2,
                    "properties": [],
                    "versatile_damage_dice": None,
                    "normal_range": None,
                    "long_range": None,
                }
            ],
        }
    )

    assert pack.armor["training_leather"].base_ac == 11
    assert pack.shields["practice_shield"].ac_bonus == 1
    assert pack.weapons["practice_sword"].damage_type == "bludgeoning"


def test_equipment_pack_loads_json_file(tmp_path: Path) -> None:
    path = tmp_path / "equipment.json"
    path.write_text(
        """
        {
          "armor": [],
          "shields": [],
          "weapons": [
            {
              "id": "wand",
              "name": "Wand",
              "category": "simple",
              "range_type": "ranged",
              "damage_dice": "1d4",
              "damage_type": "force",
              "cost_cp": 100,
              "weight_lb": 1,
              "properties": [],
              "versatile_damage_dice": null,
              "normal_range": 20,
              "long_range": 60
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    pack = load_equipment_pack(path)

    assert pack.weapons["wand"].normal_range == 20


def test_equipment_pack_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="missing sections"):
        load_equipment_pack_data({"armor": [], "weapons": []})

    with pytest.raises(ValueError, match="unknown sections"):
        load_equipment_pack_data({"armor": [], "shields": [], "weapons": [], "treasure": []})

    with pytest.raises(ValueError, match="unknown fields"):
        load_equipment_pack_data(
            {
                "armor": [
                    {
                        "id": "leather_plus",
                        "name": "Leather Plus",
                        "category": "light",
                        "base_ac": 12,
                        "cost_cp": 0,
                        "weight_lb": 10,
                        "max_dex_bonus": None,
                        "strength_requirement": None,
                        "stealth_disadvantage": False,
                        "rarity": "common",
                    }
                ],
                "shields": [],
                "weapons": [],
            }
        )

    with pytest.raises(ValueError, match="duplicate weapon id"):
        load_equipment_pack_data(
            {
                "armor": [],
                "shields": [],
                "weapons": [
                    {
                        "id": "club",
                        "name": "Club",
                        "category": "simple",
                        "range_type": "melee",
                        "damage_dice": "1d4",
                        "damage_type": "bludgeoning",
                        "cost_cp": 0,
                        "weight_lb": 1,
                        "properties": [],
                        "versatile_damage_dice": None,
                        "normal_range": None,
                        "long_range": None,
                    },
                    {
                        "id": "club",
                        "name": "Club Copy",
                        "category": "simple",
                        "range_type": "melee",
                        "damage_dice": "1d4",
                        "damage_type": "bludgeoning",
                        "cost_cp": 0,
                        "weight_lb": 1,
                        "properties": [],
                        "versatile_damage_dice": None,
                        "normal_range": None,
                        "long_range": None,
                    },
                ],
            }
        )


def character_with(strength: int, dexterity: int, level: int = 1) -> CharacterRules:
    return CharacterRules(
        level=level,
        abilities={
            "str": strength,
            "dex": dexterity,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
        },
    )
