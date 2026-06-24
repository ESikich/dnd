from dnd5e import (
    ARMOR,
    SHIELDS,
    WEAPONS,
    ArmorClassResult,
    ArmorDefinition,
    CharacterRules,
    ShieldDefinition,
    WeaponAttackProfile,
    WeaponDefinition,
    armor_class,
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
