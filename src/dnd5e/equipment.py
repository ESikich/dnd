from __future__ import annotations

from dataclasses import dataclass

from dnd5e.character import CharacterRules, ability_bonus
from dnd5e.abilities import proficiency_bonus
from dnd5e.dice import parse_dice_notation
from dnd5e.types import (
    Ability,
    ArmorCategory,
    DamageType,
    WeaponCategory,
    WeaponProperty,
    WeaponRangeType,
)

ARMOR_CATEGORIES: tuple[ArmorCategory, ...] = ("light", "medium", "heavy")
DAMAGE_TYPES: tuple[DamageType, ...] = (
    "acid",
    "bludgeoning",
    "cold",
    "fire",
    "force",
    "lightning",
    "necrotic",
    "piercing",
    "poison",
    "psychic",
    "radiant",
    "slashing",
    "thunder",
)
WEAPON_CATEGORIES: tuple[WeaponCategory, ...] = ("simple", "martial")
WEAPON_RANGE_TYPES: tuple[WeaponRangeType, ...] = ("melee", "ranged")
WEAPON_PROPERTIES: tuple[WeaponProperty, ...] = (
    "ammunition",
    "finesse",
    "heavy",
    "light",
    "loading",
    "range",
    "reach",
    "special",
    "thrown",
    "two_handed",
    "versatile",
)


@dataclass(frozen=True)
class ArmorDefinition:
    """Armor catalog entry used to calculate AC from category, base AC, and limits."""

    id: str
    name: str
    category: ArmorCategory
    base_ac: int
    cost_cp: int
    weight_lb: float
    max_dex_bonus: int | None = None
    strength_requirement: int | None = None
    stealth_disadvantage: bool = False

    def __post_init__(self) -> None:
        _validate_id(self.id, "armor id")
        _validate_name(self.name, "armor name")
        if self.category not in ARMOR_CATEGORIES:
            raise ValueError(f"unknown armor category: {self.category}")
        if self.base_ac < 1:
            raise ValueError("armor base AC must be positive")
        _validate_non_negative(self.cost_cp, "armor cost")
        _validate_non_negative(self.weight_lb, "armor weight")
        if self.max_dex_bonus is not None and self.max_dex_bonus < 0:
            raise ValueError("armor max dexterity bonus cannot be negative")
        if self.strength_requirement is not None and not 1 <= self.strength_requirement <= 30:
            raise ValueError("armor strength requirement must be from 1 to 30")


@dataclass(frozen=True)
class ShieldDefinition:
    """Shield catalog entry that contributes a fixed AC bonus."""

    id: str
    name: str
    ac_bonus: int
    cost_cp: int
    weight_lb: float

    def __post_init__(self) -> None:
        _validate_id(self.id, "shield id")
        _validate_name(self.name, "shield name")
        if self.ac_bonus < 1:
            raise ValueError("shield AC bonus must be positive")
        _validate_non_negative(self.cost_cp, "shield cost")
        _validate_non_negative(self.weight_lb, "shield weight")


@dataclass(frozen=True)
class WeaponDefinition:
    """Weapon catalog entry used for attack bonus, damage dice, and range metadata."""

    id: str
    name: str
    category: WeaponCategory
    range_type: WeaponRangeType
    damage_dice: str
    damage_type: DamageType
    cost_cp: int
    weight_lb: float
    properties: tuple[WeaponProperty, ...] = ()
    versatile_damage_dice: str | None = None
    normal_range: int | None = None
    long_range: int | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "weapon id")
        _validate_name(self.name, "weapon name")
        if self.category not in WEAPON_CATEGORIES:
            raise ValueError(f"unknown weapon category: {self.category}")
        if self.range_type not in WEAPON_RANGE_TYPES:
            raise ValueError(f"unknown weapon range type: {self.range_type}")
        _validate_damage_expression(self.damage_dice, "weapon damage dice")
        if self.damage_type not in DAMAGE_TYPES:
            raise ValueError(f"unknown weapon damage type: {self.damage_type}")
        _validate_non_negative(self.cost_cp, "weapon cost")
        _validate_non_negative(self.weight_lb, "weapon weight")
        for prop in self.properties:
            if prop not in WEAPON_PROPERTIES:
                raise ValueError(f"unknown weapon property: {prop}")
        if self.versatile_damage_dice is not None:
            if "versatile" not in self.properties:
                raise ValueError("versatile damage dice require the versatile property")
            _validate_damage_expression(self.versatile_damage_dice, "versatile damage dice")
        _validate_weapon_ranges(self.normal_range, self.long_range)


@dataclass(frozen=True)
class ArmorClassResult:
    """Computed armor class breakdown including armor, Dexterity, shield, and bonuses."""

    total: int
    base: int
    dexterity_bonus: int
    shield_bonus: int
    bonus: int
    armor: ArmorDefinition | None = None
    shield: ShieldDefinition | None = None


@dataclass(frozen=True)
class WeaponAttackProfile:
    """Resolved attack and damage values for one weapon in a character's hands."""

    weapon: WeaponDefinition
    ability: Ability
    attack_bonus: int
    damage_dice: str
    damage_bonus: int
    damage_type: DamageType
    proficient: bool
    two_handed: bool = False


def _validate_id(value: str, context: str) -> None:
    if not value:
        raise ValueError(f"{context} is required")


def _validate_name(value: str, context: str) -> None:
    if not value:
        raise ValueError(f"{context} is required")


def _validate_non_negative(value: float, context: str) -> None:
    if value < 0:
        raise ValueError(f"{context} cannot be negative")


def _validate_damage_expression(value: str, context: str) -> None:
    try:
        flat_damage = int(value)
    except ValueError:
        parse_dice_notation(value)
        return

    if flat_damage < 0:
        raise ValueError(f"{context} cannot be negative")


def _validate_weapon_ranges(normal_range: int | None, long_range: int | None) -> None:
    if (normal_range is None) != (long_range is None):
        raise ValueError("weapon ranges must include both normal and long range")
    if normal_range is None or long_range is None:
        return
    if normal_range < 1:
        raise ValueError("weapon normal range must be positive")
    if long_range < normal_range:
        raise ValueError("weapon long range must be at least normal range")


ARMOR: dict[str, ArmorDefinition] = {
    "padded": ArmorDefinition("padded", "Padded", "light", 11, 500, 8, stealth_disadvantage=True),
    "leather": ArmorDefinition("leather", "Leather", "light", 11, 1000, 10),
    "studded_leather": ArmorDefinition("studded_leather", "Studded Leather", "light", 12, 4500, 13),
    "hide": ArmorDefinition("hide", "Hide", "medium", 12, 1000, 12, max_dex_bonus=2),
    "chain_shirt": ArmorDefinition("chain_shirt", "Chain Shirt", "medium", 13, 5000, 20, max_dex_bonus=2),
    "scale_mail": ArmorDefinition(
        "scale_mail",
        "Scale Mail",
        "medium",
        14,
        5000,
        45,
        max_dex_bonus=2,
        stealth_disadvantage=True,
    ),
    "breastplate": ArmorDefinition("breastplate", "Breastplate", "medium", 14, 40000, 20, max_dex_bonus=2),
    "half_plate": ArmorDefinition(
        "half_plate",
        "Half Plate",
        "medium",
        15,
        75000,
        40,
        max_dex_bonus=2,
        stealth_disadvantage=True,
    ),
    "ring_mail": ArmorDefinition(
        "ring_mail",
        "Ring Mail",
        "heavy",
        14,
        3000,
        40,
        stealth_disadvantage=True,
    ),
    "chain_mail": ArmorDefinition(
        "chain_mail",
        "Chain Mail",
        "heavy",
        16,
        7500,
        55,
        strength_requirement=13,
        stealth_disadvantage=True,
    ),
    "splint": ArmorDefinition(
        "splint",
        "Splint",
        "heavy",
        17,
        20000,
        60,
        strength_requirement=15,
        stealth_disadvantage=True,
    ),
    "plate": ArmorDefinition(
        "plate",
        "Plate",
        "heavy",
        18,
        150000,
        65,
        strength_requirement=15,
        stealth_disadvantage=True,
    ),
}

SHIELDS: dict[str, ShieldDefinition] = {
    "shield": ShieldDefinition("shield", "Shield", 2, 1000, 6),
}

WEAPONS: dict[str, WeaponDefinition] = {
    "club": WeaponDefinition("club", "Club", "simple", "melee", "1d4", "bludgeoning", 10, 2, ("light",)),
    "dagger": WeaponDefinition(
        "dagger",
        "Dagger",
        "simple",
        "melee",
        "1d4",
        "piercing",
        200,
        1,
        ("finesse", "light", "thrown"),
        normal_range=20,
        long_range=60,
    ),
    "greatclub": WeaponDefinition(
        "greatclub", "Greatclub", "simple", "melee", "1d8", "bludgeoning", 20, 10, ("two_handed",)
    ),
    "handaxe": WeaponDefinition(
        "handaxe",
        "Handaxe",
        "simple",
        "melee",
        "1d6",
        "slashing",
        500,
        2,
        ("light", "thrown"),
        normal_range=20,
        long_range=60,
    ),
    "javelin": WeaponDefinition(
        "javelin", "Javelin", "simple", "melee", "1d6", "piercing", 50, 2, ("thrown",), normal_range=30, long_range=120
    ),
    "light_hammer": WeaponDefinition(
        "light_hammer",
        "Light Hammer",
        "simple",
        "melee",
        "1d4",
        "bludgeoning",
        200,
        2,
        ("light", "thrown"),
        normal_range=20,
        long_range=60,
    ),
    "mace": WeaponDefinition("mace", "Mace", "simple", "melee", "1d6", "bludgeoning", 500, 4),
    "quarterstaff": WeaponDefinition(
        "quarterstaff",
        "Quarterstaff",
        "simple",
        "melee",
        "1d6",
        "bludgeoning",
        20,
        4,
        ("versatile",),
        versatile_damage_dice="1d8",
    ),
    "sickle": WeaponDefinition("sickle", "Sickle", "simple", "melee", "1d4", "slashing", 100, 2, ("light",)),
    "spear": WeaponDefinition(
        "spear",
        "Spear",
        "simple",
        "melee",
        "1d6",
        "piercing",
        100,
        3,
        ("thrown", "versatile"),
        versatile_damage_dice="1d8",
        normal_range=20,
        long_range=60,
    ),
    "light_crossbow": WeaponDefinition(
        "light_crossbow",
        "Light Crossbow",
        "simple",
        "ranged",
        "1d8",
        "piercing",
        2500,
        5,
        ("ammunition", "loading", "two_handed"),
        normal_range=80,
        long_range=320,
    ),
    "dart": WeaponDefinition(
        "dart",
        "Dart",
        "simple",
        "ranged",
        "1d4",
        "piercing",
        5,
        0.25,
        ("finesse", "thrown"),
        normal_range=20,
        long_range=60,
    ),
    "shortbow": WeaponDefinition(
        "shortbow",
        "Shortbow",
        "simple",
        "ranged",
        "1d6",
        "piercing",
        2500,
        2,
        ("ammunition", "two_handed"),
        normal_range=80,
        long_range=320,
    ),
    "sling": WeaponDefinition(
        "sling", "Sling", "simple", "ranged", "1d4", "bludgeoning", 10, 0, ("ammunition",), normal_range=30, long_range=120
    ),
    "battleaxe": WeaponDefinition(
        "battleaxe",
        "Battleaxe",
        "martial",
        "melee",
        "1d8",
        "slashing",
        1000,
        4,
        ("versatile",),
        versatile_damage_dice="1d10",
    ),
    "flail": WeaponDefinition("flail", "Flail", "martial", "melee", "1d8", "bludgeoning", 1000, 2),
    "glaive": WeaponDefinition(
        "glaive", "Glaive", "martial", "melee", "1d10", "slashing", 2000, 6, ("heavy", "reach", "two_handed")
    ),
    "greataxe": WeaponDefinition(
        "greataxe", "Greataxe", "martial", "melee", "1d12", "slashing", 3000, 7, ("heavy", "two_handed")
    ),
    "greatsword": WeaponDefinition(
        "greatsword", "Greatsword", "martial", "melee", "2d6", "slashing", 5000, 6, ("heavy", "two_handed")
    ),
    "halberd": WeaponDefinition(
        "halberd", "Halberd", "martial", "melee", "1d10", "slashing", 2000, 6, ("heavy", "reach", "two_handed")
    ),
    "lance": WeaponDefinition("lance", "Lance", "martial", "melee", "1d12", "piercing", 1000, 6, ("reach", "special")),
    "longsword": WeaponDefinition(
        "longsword",
        "Longsword",
        "martial",
        "melee",
        "1d8",
        "slashing",
        1500,
        3,
        ("versatile",),
        versatile_damage_dice="1d10",
    ),
    "maul": WeaponDefinition(
        "maul", "Maul", "martial", "melee", "2d6", "bludgeoning", 1000, 10, ("heavy", "two_handed")
    ),
    "morningstar": WeaponDefinition("morningstar", "Morningstar", "martial", "melee", "1d8", "piercing", 1500, 4),
    "pike": WeaponDefinition(
        "pike", "Pike", "martial", "melee", "1d10", "piercing", 500, 18, ("heavy", "reach", "two_handed")
    ),
    "rapier": WeaponDefinition("rapier", "Rapier", "martial", "melee", "1d8", "piercing", 2500, 2, ("finesse",)),
    "scimitar": WeaponDefinition(
        "scimitar", "Scimitar", "martial", "melee", "1d6", "slashing", 2500, 3, ("finesse", "light")
    ),
    "shortsword": WeaponDefinition(
        "shortsword", "Shortsword", "martial", "melee", "1d6", "piercing", 1000, 2, ("finesse", "light")
    ),
    "trident": WeaponDefinition(
        "trident",
        "Trident",
        "martial",
        "melee",
        "1d6",
        "piercing",
        500,
        4,
        ("thrown", "versatile"),
        versatile_damage_dice="1d8",
        normal_range=20,
        long_range=60,
    ),
    "war_pick": WeaponDefinition("war_pick", "War Pick", "martial", "melee", "1d8", "piercing", 500, 2),
    "warhammer": WeaponDefinition(
        "warhammer",
        "Warhammer",
        "martial",
        "melee",
        "1d8",
        "bludgeoning",
        1500,
        2,
        ("versatile",),
        versatile_damage_dice="1d10",
    ),
    "whip": WeaponDefinition("whip", "Whip", "martial", "melee", "1d4", "slashing", 200, 3, ("finesse", "reach")),
    "blowgun": WeaponDefinition(
        "blowgun",
        "Blowgun",
        "martial",
        "ranged",
        "1",
        "piercing",
        1000,
        1,
        ("ammunition", "loading"),
        normal_range=25,
        long_range=100,
    ),
    "hand_crossbow": WeaponDefinition(
        "hand_crossbow",
        "Hand Crossbow",
        "martial",
        "ranged",
        "1d6",
        "piercing",
        7500,
        3,
        ("ammunition", "light", "loading"),
        normal_range=30,
        long_range=120,
    ),
    "heavy_crossbow": WeaponDefinition(
        "heavy_crossbow",
        "Heavy Crossbow",
        "martial",
        "ranged",
        "1d10",
        "piercing",
        5000,
        18,
        ("ammunition", "heavy", "loading", "two_handed"),
        normal_range=100,
        long_range=400,
    ),
    "longbow": WeaponDefinition(
        "longbow",
        "Longbow",
        "martial",
        "ranged",
        "1d8",
        "piercing",
        5000,
        2,
        ("ammunition", "heavy", "two_handed"),
        normal_range=150,
        long_range=600,
    ),
    "net": WeaponDefinition(
        "net",
        "Net",
        "martial",
        "ranged",
        "0",
        "bludgeoning",
        100,
        3,
        ("special", "thrown"),
        normal_range=5,
        long_range=15,
    ),
}


def armor_class(
    character: CharacterRules,
    armor: str | ArmorDefinition | None = None,
    shield: str | ShieldDefinition | None = None,
    bonuses: int = 0,
) -> ArmorClassResult:
    """Calculate armor class from character Dexterity, armor, shield, and bonuses."""

    armor_definition = _resolve_armor(armor)
    shield_definition = _resolve_shield(shield)
    dexterity = ability_bonus(character, "dex")

    if armor_definition is None:
        base = 10
        dexterity_bonus = dexterity
    elif armor_definition.category == "heavy":
        base = armor_definition.base_ac
        dexterity_bonus = 0
    else:
        base = armor_definition.base_ac
        dexterity_bonus = dexterity
        if armor_definition.max_dex_bonus is not None:
            dexterity_bonus = min(dexterity_bonus, armor_definition.max_dex_bonus)

    shield_bonus = shield_definition.ac_bonus if shield_definition else 0

    return ArmorClassResult(
        total=base + dexterity_bonus + shield_bonus + bonuses,
        base=base,
        dexterity_bonus=dexterity_bonus,
        shield_bonus=shield_bonus,
        bonus=bonuses,
        armor=armor_definition,
        shield=shield_definition,
    )


def weapon_attack_bonus(
    character: CharacterRules,
    weapon: str | WeaponDefinition,
    proficient: bool = True,
    ability: Ability | None = None,
    bonuses: int = 0,
) -> int:
    """Return a weapon attack bonus from ability, proficiency, and flat bonuses."""

    weapon_definition = _resolve_weapon(weapon)
    selected_ability = ability or weapon_ability(character, weapon_definition)
    proficiency = proficiency_bonus(character.level) if proficient else 0

    return ability_bonus(character, selected_ability) + proficiency + bonuses


def weapon_damage_dice(weapon: str | WeaponDefinition, two_handed: bool = False) -> str:
    """Return the weapon damage dice, using versatile dice when two-handed."""

    weapon_definition = _resolve_weapon(weapon)
    if two_handed and weapon_definition.versatile_damage_dice is not None:
        return weapon_definition.versatile_damage_dice
    return weapon_definition.damage_dice


def weapon_damage_bonus(
    character: CharacterRules,
    weapon: str | WeaponDefinition,
    ability: Ability | None = None,
    bonuses: int = 0,
) -> int:
    """Return a weapon damage bonus from ability and flat bonuses."""

    weapon_definition = _resolve_weapon(weapon)
    selected_ability = ability or weapon_ability(character, weapon_definition)
    return ability_bonus(character, selected_ability) + bonuses


def weapon_attack_profile(
    character: CharacterRules,
    weapon: str | WeaponDefinition,
    proficient: bool = True,
    ability: Ability | None = None,
    two_handed: bool = False,
    bonuses: int = 0,
) -> WeaponAttackProfile:
    """Return the resolved attack and damage profile for one weapon."""

    weapon_definition = _resolve_weapon(weapon)
    selected_ability = ability or weapon_ability(character, weapon_definition)

    return WeaponAttackProfile(
        weapon=weapon_definition,
        ability=selected_ability,
        attack_bonus=weapon_attack_bonus(character, weapon_definition, proficient, selected_ability, bonuses),
        damage_dice=weapon_damage_dice(weapon_definition, two_handed),
        damage_bonus=weapon_damage_bonus(character, weapon_definition, selected_ability, bonuses),
        damage_type=weapon_definition.damage_type,
        proficient=proficient,
        two_handed=two_handed,
    )


def weapon_ability(character: CharacterRules, weapon: str | WeaponDefinition) -> Ability:
    """Choose the default attack ability for a weapon and character."""

    weapon_definition = _resolve_weapon(weapon)

    if "finesse" in weapon_definition.properties:
        return "dex" if ability_bonus(character, "dex") > ability_bonus(character, "str") else "str"

    if weapon_definition.range_type == "ranged":
        return "dex"

    return "str"


def _resolve_armor(armor: str | ArmorDefinition | None) -> ArmorDefinition | None:
    if armor is None or isinstance(armor, ArmorDefinition):
        return armor
    return ARMOR[armor]


def _resolve_shield(shield: str | ShieldDefinition | None) -> ShieldDefinition | None:
    if shield is None or isinstance(shield, ShieldDefinition):
        return shield
    return SHIELDS[shield]


def _resolve_weapon(weapon: str | WeaponDefinition) -> WeaponDefinition:
    if isinstance(weapon, WeaponDefinition):
        return weapon
    return WEAPONS[weapon]
