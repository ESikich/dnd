from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from dnd5e.abilities import ability_modifier
from dnd5e.character import (
    CharacterRules,
    initiative_bonus,
    passive_skill,
    saving_throw_bonus,
    skill_bonus,
)
from dnd5e.classes import SRD_CLASSES
from dnd5e.equipment import (
    ARMOR,
    SHIELDS,
    WEAPONS,
    ArmorClassResult,
    WeaponAttackProfile,
    armor_class,
    weapon_attack_profile,
)
from dnd5e.hit_points import HitPointState
from dnd5e.skills import SKILL_ABILITIES
from dnd5e.spells import spell_attack_bonus, spell_save_dc
from dnd5e.types import Ability, CharacterClassName, ConditionName, ProficiencyLevel, Skill

if TYPE_CHECKING:
    from dnd5e.combat import Combatant

ABILITIES: tuple[Ability, ...] = ("str", "dex", "con", "int", "wis", "cha")
PROFICIENCY_LEVELS: tuple[ProficiencyLevel, ...] = ("none", "half", "proficient", "expertise")


@dataclass(frozen=True)
class CharacterClassLevel:
    """One class and level entry within a character sheet."""

    name: CharacterClassName
    level: int

    def __post_init__(self) -> None:
        if self.name not in SRD_CLASSES:
            raise ValueError(f"unknown class: {self.name}")
        if not 1 <= self.level <= 20:
            raise ValueError("class level must be from 1 to 20")


@dataclass(frozen=True)
class CharacterLoadout:
    """Equipped item IDs and flat bonuses used by sheet-derived combat stats."""

    armor: str | None = None
    shield: str | None = None
    weapons: tuple[str, ...] = ()
    two_handed_weapons: tuple[str, ...] = ()
    armor_class_bonus: int = 0
    weapon_attack_bonus: int = 0


@dataclass(frozen=True)
class CharacterSheet:
    """Validated character record for classes, abilities, proficiencies, HP, and loadout."""

    id: str
    name: str
    classes: tuple[CharacterClassLevel, ...]
    abilities: dict[Ability, int]
    skill_proficiencies: dict[Skill, ProficiencyLevel] = field(default_factory=dict)
    saving_throw_proficiencies: dict[Ability, ProficiencyLevel] = field(default_factory=dict)
    skill_bonuses: dict[Skill, int] = field(default_factory=dict)
    saving_throw_bonuses: dict[Ability, int] = field(default_factory=dict)
    initiative_bonus_value: int = 0
    loadout: CharacterLoadout = field(default_factory=CharacterLoadout)
    maximum_hit_points: int | None = None
    current_hit_points: int | None = None
    temporary_hit_points: int = 0
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.classes:
            raise ValueError("character sheet requires at least one class")
        if not self.id:
            raise ValueError("character id is required")
        if not self.name:
            raise ValueError("character name is required")

        level = character_sheet_level(self)
        if not 1 <= level <= 20:
            raise ValueError("total character level must be from 1 to 20")

        missing = tuple(ability for ability in ABILITIES if ability not in self.abilities)
        if missing:
            raise ValueError(f"missing ability scores: {', '.join(missing)}")
        for ability, score in self.abilities.items():
            if ability not in ABILITIES:
                raise ValueError(f"unknown ability: {ability}")
            if not 1 <= score <= 30:
                raise ValueError(f"{ability} score must be from 1 to 30")

        _validate_skill_proficiencies(self.skill_proficiencies)
        _validate_ability_proficiencies(self.saving_throw_proficiencies)
        _validate_skill_bonus_keys(self.skill_bonuses)
        _validate_ability_bonus_keys(self.saving_throw_bonuses)
        _validate_loadout(self.loadout)

        if self.maximum_hit_points is not None and self.maximum_hit_points < 1:
            raise ValueError("maximum hit points must be positive")
        if self.current_hit_points is not None:
            maximum = self.maximum_hit_points or character_sheet_max_hit_points(self)
            if not 0 <= self.current_hit_points <= maximum:
                raise ValueError("current hit points must be from 0 to maximum hit points")
        if self.temporary_hit_points < 0:
            raise ValueError("temporary hit points cannot be negative")


def character_sheet_level(sheet: CharacterSheet) -> int:
    """Return total character level across all class entries."""

    return sum(class_level.level for class_level in sheet.classes)


def character_sheet_rules(sheet: CharacterSheet) -> CharacterRules:
    """Project a sheet into the smaller rules object used by derived math helpers."""

    return CharacterRules(
        level=character_sheet_level(sheet),
        abilities=sheet.abilities,
        skill_proficiencies=sheet.skill_proficiencies,
        saving_throw_proficiencies=sheet.saving_throw_proficiencies,
        skill_bonuses=sheet.skill_bonuses,
        saving_throw_bonuses=sheet.saving_throw_bonuses,
        initiative_bonus_value=sheet.initiative_bonus_value,
    )


def character_sheet_max_hit_points(sheet: CharacterSheet, first_level_max: bool = True) -> int:
    """Return maximum HP from explicit sheet HP or class hit dice and Constitution."""

    if sheet.maximum_hit_points is not None:
        return sheet.maximum_hit_points

    constitution_modifier = ability_modifier(sheet.abilities["con"])
    total = 0
    first_character_level = True

    for class_level in sheet.classes:
        hit_die = SRD_CLASSES[class_level.name].hit_die
        for _ in range(class_level.level):
            total += hit_die if first_character_level and first_level_max else _average_hit_die(hit_die)
            total += constitution_modifier
            first_character_level = False

    return max(1, total)


def character_sheet_hit_points(sheet: CharacterSheet) -> HitPointState:
    """Return runtime HP state from sheet maximum, current, and temporary HP fields."""

    maximum = character_sheet_max_hit_points(sheet)
    current = maximum if sheet.current_hit_points is None else sheet.current_hit_points
    return HitPointState(
        current=current,
        maximum=maximum,
        temporary=sheet.temporary_hit_points,
    )


def character_sheet_armor_class(sheet: CharacterSheet) -> ArmorClassResult:
    """Return the armor class breakdown for the sheet's current loadout."""

    return armor_class(
        character_sheet_rules(sheet),
        armor=sheet.loadout.armor,
        shield=sheet.loadout.shield,
        bonuses=sheet.loadout.armor_class_bonus,
    )


def character_sheet_weapon_profile(
    sheet: CharacterSheet,
    weapon: str,
    *,
    two_handed: bool | None = None,
) -> WeaponAttackProfile:
    """Return attack and damage values for one weapon used by the sheet."""

    use_two_handed = weapon in sheet.loadout.two_handed_weapons if two_handed is None else two_handed
    return weapon_attack_profile(
        character_sheet_rules(sheet),
        weapon,
        proficient=_is_weapon_proficient(sheet, weapon),
        two_handed=use_two_handed,
        bonuses=sheet.loadout.weapon_attack_bonus,
    )


def character_sheet_weapon_profiles(sheet: CharacterSheet) -> tuple[WeaponAttackProfile, ...]:
    """Return attack profiles for every weapon listed in the sheet loadout."""

    return tuple(character_sheet_weapon_profile(sheet, weapon) for weapon in sheet.loadout.weapons)


def character_sheet_skill_bonus(sheet: CharacterSheet, skill: Skill) -> int:
    """Return a skill bonus derived from the sheet's abilities and proficiencies."""

    return skill_bonus(character_sheet_rules(sheet), skill)


def character_sheet_passive_skill(sheet: CharacterSheet, skill: Skill) -> int:
    """Return a passive skill score derived from the sheet."""

    return passive_skill(character_sheet_rules(sheet), skill)


def character_sheet_saving_throw_bonus(sheet: CharacterSheet, ability: Ability) -> int:
    """Return a saving throw bonus derived from the sheet."""

    return saving_throw_bonus(character_sheet_rules(sheet), ability)


def character_sheet_spell_attack_bonus(sheet: CharacterSheet, ability: Ability, bonus: int = 0) -> int:
    """Return spell attack bonus derived from the sheet."""

    return spell_attack_bonus(character_sheet_rules(sheet), ability, bonus)


def character_sheet_spell_save_dc(sheet: CharacterSheet, ability: Ability, bonus: int = 0) -> int:
    """Return spell save DC derived from the sheet."""

    return spell_save_dc(character_sheet_rules(sheet), ability, bonus)


def character_sheet_initiative_bonus(sheet: CharacterSheet) -> int:
    """Return initiative bonus derived from the sheet."""

    return initiative_bonus(character_sheet_rules(sheet))


def character_sheet_combatant(
    sheet: CharacterSheet,
    *,
    roll: int = 0,
    conditions: tuple[ConditionName, ...] = (),
) -> Combatant:
    """Create a runtime combatant from sheet-derived initiative, AC, and HP."""

    from dnd5e.combat import create_combatant

    return create_combatant(
        id=sheet.id,
        name=sheet.name,
        initiative_bonus=character_sheet_initiative_bonus(sheet),
        roll=roll,
        armor_class=character_sheet_armor_class(sheet).total,
        hit_points=character_sheet_hit_points(sheet),
        conditions=conditions,
        source=sheet,
    )


def _is_weapon_proficient(sheet: CharacterSheet, weapon: str) -> bool:
    weapon_definition = WEAPONS[weapon]
    training = {
        trained
        for class_level in sheet.classes
        for trained in SRD_CLASSES[class_level.name].weapon_training
    }
    return weapon_definition.category in training


def _average_hit_die(hit_die: int) -> int:
    return (hit_die // 2) + 1


def _validate_skill_proficiencies(proficiencies: dict[Skill, ProficiencyLevel]) -> None:
    for skill, proficiency in proficiencies.items():
        if skill not in SKILL_ABILITIES:
            raise ValueError(f"unknown skill proficiency: {skill}")
        _validate_proficiency_level(proficiency, f"skill proficiency for {skill}")


def _validate_ability_proficiencies(proficiencies: dict[Ability, ProficiencyLevel]) -> None:
    for ability, proficiency in proficiencies.items():
        if ability not in ABILITIES:
            raise ValueError(f"unknown saving throw proficiency: {ability}")
        _validate_proficiency_level(proficiency, f"saving throw proficiency for {ability}")


def _validate_skill_bonus_keys(bonuses: dict[Skill, int]) -> None:
    for skill in bonuses:
        if skill not in SKILL_ABILITIES:
            raise ValueError(f"unknown skill bonus: {skill}")


def _validate_ability_bonus_keys(bonuses: dict[Ability, int]) -> None:
    for ability in bonuses:
        if ability not in ABILITIES:
            raise ValueError(f"unknown saving throw bonus: {ability}")


def _validate_proficiency_level(proficiency: ProficiencyLevel, context: str) -> None:
    if proficiency not in PROFICIENCY_LEVELS:
        raise ValueError(f"unknown {context}: {proficiency}")


def _validate_loadout(loadout: CharacterLoadout) -> None:
    if loadout.armor is not None and loadout.armor not in ARMOR:
        raise ValueError(f"unknown armor: {loadout.armor}")
    if loadout.shield is not None and loadout.shield not in SHIELDS:
        raise ValueError(f"unknown shield: {loadout.shield}")

    for weapon in loadout.weapons:
        if weapon not in WEAPONS:
            raise ValueError(f"unknown weapon: {weapon}")

    equipped_weapons = set(loadout.weapons)
    for weapon in loadout.two_handed_weapons:
        if weapon not in WEAPONS:
            raise ValueError(f"unknown two-handed weapon: {weapon}")
        if weapon not in equipped_weapons:
            raise ValueError(f"two-handed weapon is not equipped: {weapon}")
