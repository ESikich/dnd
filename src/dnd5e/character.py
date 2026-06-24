from __future__ import annotations

from dataclasses import dataclass, field

from dnd5e.abilities import ability_modifier, passive_score, proficiency_bonus, proficiency_value
from dnd5e.skills import SKILL_ABILITIES
from dnd5e.types import Ability, ProficiencyLevel, Skill

ABILITIES: tuple[Ability, ...] = ("str", "dex", "con", "int", "wis", "cha")
PROFICIENCY_LEVELS: tuple[ProficiencyLevel, ...] = ("none", "half", "proficient", "expertise")


@dataclass(frozen=True)
class CharacterRules:
    """Core level, ability, proficiency, and bonus inputs for derived rules math."""

    level: int
    abilities: dict[Ability, int]
    skill_proficiencies: dict[Skill, ProficiencyLevel] = field(default_factory=dict)
    saving_throw_proficiencies: dict[Ability, ProficiencyLevel] = field(default_factory=dict)
    skill_bonuses: dict[Skill, int] = field(default_factory=dict)
    saving_throw_bonuses: dict[Ability, int] = field(default_factory=dict)
    initiative_bonus_value: int = 0

    def __post_init__(self) -> None:
        if not 1 <= self.level <= 20:
            raise ValueError("level must be from 1 to 20")

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


def ability_bonus(character: CharacterRules, ability: Ability) -> int:
    return ability_modifier(character.abilities[ability])


def skill_bonus(character: CharacterRules, skill: Skill) -> int:
    ability = SKILL_ABILITIES[skill]
    proficiency = character.skill_proficiencies.get(skill, "none")

    return (
        ability_bonus(character, ability)
        + proficiency_value(proficiency, proficiency_bonus(character.level))
        + character.skill_bonuses.get(skill, 0)
    )


def passive_skill(character: CharacterRules, skill: Skill) -> int:
    ability = SKILL_ABILITIES[skill]
    proficiency = character.skill_proficiencies.get(skill, "none")

    return passive_score(
        ability_bonus(character, ability),
        proficiency_value(proficiency, proficiency_bonus(character.level)),
        character.skill_bonuses.get(skill, 0),
    )


def saving_throw_bonus(character: CharacterRules, ability: Ability) -> int:
    proficiency = character.saving_throw_proficiencies.get(ability, "none")

    return (
        ability_bonus(character, ability)
        + proficiency_value(proficiency, proficiency_bonus(character.level))
        + character.saving_throw_bonuses.get(ability, 0)
    )


def initiative_bonus(character: CharacterRules) -> int:
    return ability_bonus(character, "dex") + character.initiative_bonus_value


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
