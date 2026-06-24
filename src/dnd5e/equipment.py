from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, TypeVar

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
T = TypeVar("T")


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


@dataclass(frozen=True)
class EquipmentPack:
    """Loaded equipment content grouped into armor, shield, and weapon catalogs."""

    armor: dict[str, ArmorDefinition]
    shields: dict[str, ShieldDefinition]
    weapons: dict[str, WeaponDefinition]


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


def load_equipment_pack(path: str | Path) -> EquipmentPack:
    """Load armor, shields, and weapons from an equipment content-pack JSON file."""

    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("equipment content pack must be a JSON object")
    return load_equipment_pack_data(data)


def load_builtin_equipment_pack() -> EquipmentPack:
    """Load the packaged SRD-style equipment content pack."""

    data_resource = files("dnd5e.data").joinpath("equipment.json")
    with data_resource.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("built-in equipment content pack must be a JSON object")
    return load_equipment_pack_data(data)


def load_equipment_pack_data(data: Mapping[str, Any]) -> EquipmentPack:
    """Validate and construct an equipment pack from decoded JSON-style data."""

    _validate_pack_keys(data)
    armor = _load_armor_entries(data["armor"])
    shields = _load_shield_entries(data["shields"])
    weapons = _load_weapon_entries(data["weapons"])
    return EquipmentPack(armor=armor, shields=shields, weapons=weapons)


def _validate_pack_keys(data: Mapping[str, Any]) -> None:
    expected = {"armor", "shields", "weapons"}
    missing = expected - set(data)
    if missing:
        raise ValueError(f"equipment content pack missing sections: {', '.join(sorted(missing))}")
    extra = set(data) - expected
    if extra:
        raise ValueError(f"equipment content pack has unknown sections: {', '.join(sorted(extra))}")


def _load_armor_entries(entries: Any) -> dict[str, ArmorDefinition]:
    return _catalog_by_id(
        "armor",
        [
            ArmorDefinition(
                id=_field(entry, "id", str, "armor"),
                name=_field(entry, "name", str, "armor"),
                category=_field(entry, "category", str, "armor"),  # type: ignore[arg-type]
                base_ac=_field(entry, "base_ac", int, "armor"),
                cost_cp=_field(entry, "cost_cp", int, "armor"),
                weight_lb=_number_field(entry, "weight_lb", "armor"),
                max_dex_bonus=_optional_field(entry, "max_dex_bonus", int, "armor"),
                strength_requirement=_optional_field(entry, "strength_requirement", int, "armor"),
                stealth_disadvantage=_field(entry, "stealth_disadvantage", bool, "armor"),
            )
            for entry in _validated_entries(
                entries,
                "armor",
                {
                    "id",
                    "name",
                    "category",
                    "base_ac",
                    "cost_cp",
                    "weight_lb",
                    "max_dex_bonus",
                    "strength_requirement",
                    "stealth_disadvantage",
                },
            )
        ],
    )


def _load_shield_entries(entries: Any) -> dict[str, ShieldDefinition]:
    return _catalog_by_id(
        "shield",
        [
            ShieldDefinition(
                id=_field(entry, "id", str, "shield"),
                name=_field(entry, "name", str, "shield"),
                ac_bonus=_field(entry, "ac_bonus", int, "shield"),
                cost_cp=_field(entry, "cost_cp", int, "shield"),
                weight_lb=_number_field(entry, "weight_lb", "shield"),
            )
            for entry in _validated_entries(
                entries,
                "shields",
                {"id", "name", "ac_bonus", "cost_cp", "weight_lb"},
            )
        ],
    )


def _load_weapon_entries(entries: Any) -> dict[str, WeaponDefinition]:
    return _catalog_by_id(
        "weapon",
        [
            WeaponDefinition(
                id=_field(entry, "id", str, "weapon"),
                name=_field(entry, "name", str, "weapon"),
                category=_field(entry, "category", str, "weapon"),  # type: ignore[arg-type]
                range_type=_field(entry, "range_type", str, "weapon"),  # type: ignore[arg-type]
                damage_dice=_field(entry, "damage_dice", str, "weapon"),
                damage_type=_field(entry, "damage_type", str, "weapon"),  # type: ignore[arg-type]
                cost_cp=_field(entry, "cost_cp", int, "weapon"),
                weight_lb=_number_field(entry, "weight_lb", "weapon"),
                properties=tuple(_string_list_field(entry, "properties", "weapon")),  # type: ignore[arg-type]
                versatile_damage_dice=_optional_field(entry, "versatile_damage_dice", str, "weapon"),
                normal_range=_optional_field(entry, "normal_range", int, "weapon"),
                long_range=_optional_field(entry, "long_range", int, "weapon"),
            )
            for entry in _validated_entries(
                entries,
                "weapons",
                {
                    "id",
                    "name",
                    "category",
                    "range_type",
                    "damage_dice",
                    "damage_type",
                    "cost_cp",
                    "weight_lb",
                    "properties",
                    "versatile_damage_dice",
                    "normal_range",
                    "long_range",
                },
            )
        ],
    )


def _validated_entries(
    entries: Any, section: str, expected_fields: set[str]
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(entries, list):
        raise ValueError(f"equipment content section {section} must be a list")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError(f"equipment content section {section} entries must be objects")
        extra = set(entry) - expected_fields
        if extra:
            raise ValueError(f"{section} entry has unknown fields: {', '.join(sorted(extra))}")
    return tuple(entries)


def _catalog_by_id(section: str, entries: list[T]) -> dict[str, T]:
    catalog: dict[str, T] = {}
    for entry in entries:
        entry_id = getattr(entry, "id")
        if entry_id in catalog:
            raise ValueError(f"duplicate {section} id: {entry_id}")
        catalog[entry_id] = entry
    return catalog


def _field(entry: Mapping[str, Any], name: str, expected_type: type[T] | Any, section: str) -> T:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__}")
    return value


def _optional_field(
    entry: Mapping[str, Any], name: str, expected_type: type[T], section: str
) -> T | None:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if value is None:
        return None
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__} or null")
    return value


def _number_field(entry: Mapping[str, Any], name: str, section: str) -> float:
    value = _field(entry, name, int | float, section)
    return float(value)


def _string_list_field(entry: Mapping[str, Any], name: str, section: str) -> tuple[str, ...]:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, list):
        raise ValueError(f"{section}.{name} must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{section}.{name} entries must be strings")
    return tuple(value)


_BUILTIN_EQUIPMENT = load_builtin_equipment_pack()
ARMOR: dict[str, ArmorDefinition] = _BUILTIN_EQUIPMENT.armor
SHIELDS: dict[str, ShieldDefinition] = _BUILTIN_EQUIPMENT.shields
WEAPONS: dict[str, WeaponDefinition] = _BUILTIN_EQUIPMENT.weapons


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
