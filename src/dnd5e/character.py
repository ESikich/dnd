from __future__ import annotations

from dataclasses import dataclass, field

from dnd5e.abilities import ability_modifier, passive_score, proficiency_bonus, proficiency_value
from dnd5e.skills import SKILL_ABILITIES
from dnd5e.types import Ability, ProficiencyLevel, Skill


@dataclass(frozen=True)
class CharacterRules:
    level: int
    abilities: dict[Ability, int]
    skill_proficiencies: dict[Skill, ProficiencyLevel] = field(default_factory=dict)
    saving_throw_proficiencies: dict[Ability, ProficiencyLevel] = field(default_factory=dict)
    skill_bonuses: dict[Skill, int] = field(default_factory=dict)
    saving_throw_bonuses: dict[Ability, int] = field(default_factory=dict)
    initiative_bonus_value: int = 0


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
