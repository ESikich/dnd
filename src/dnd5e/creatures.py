from __future__ import annotations

from dataclasses import dataclass
from random import random

from dnd5e.abilities import RandomSource, ability_modifier
from dnd5e.combat import (
    AttackRollResult,
    CONDITION_NAMES,
    Combatant,
    DAMAGE_TYPES,
    DamageResult,
    attack_roll,
    create_combatant,
    damage_roll,
)
from dnd5e.dice import parse_dice_notation
from dnd5e.hit_points import HitPointState
from dnd5e.skills import SKILL_ABILITIES
from dnd5e.types import Ability, ConditionName, CreatureSize, CreatureType, DamageType, Skill

_ABILITIES: tuple[Ability, ...] = ("str", "dex", "con", "int", "wis", "cha")
_SKILLS: tuple[Skill, ...] = tuple(SKILL_ABILITIES)


@dataclass(frozen=True)
class CreatureFeature:
    """Named creature mechanics metadata such as a trait, bonus action, or reaction."""

    name: str
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("creature feature name is required")
        for tag in self.tags:
            if not tag:
                raise ValueError("creature feature tags cannot be empty")


@dataclass(frozen=True)
class CreatureAction:
    """A combat action from a creature stat block.

    Actions model attack bonus, damage dice, damage type, and basic reach/range
    metadata without long-form rule text.
    """

    name: str
    attack_bonus: int
    damage_dice: str
    damage_type: DamageType
    reach: int | None = None
    normal_range: int | None = None
    long_range: int | None = None
    target: str = "one target"

    def __post_init__(self) -> None:
        parse_dice_notation(self.damage_dice)
        _validate_positive_optional("reach", self.reach)
        _validate_positive_optional("normal_range", self.normal_range)
        _validate_positive_optional("long_range", self.long_range)
        if self.normal_range is not None and self.long_range is not None and self.long_range < self.normal_range:
            raise ValueError("long_range must be greater than or equal to normal_range")


@dataclass(frozen=True)
class CreatureDefinition:
    """A compact, mechanics-first creature stat block."""

    id: str
    name: str
    size: CreatureSize
    type: CreatureType
    alignment: str
    armor_class: int
    hit_points: int
    hit_dice: str
    speed: dict[str, int]
    abilities: dict[Ability, int]
    saving_throws: dict[Ability, int]
    skills: dict[Skill, int]
    senses: dict[str, int]
    languages: tuple[str, ...]
    challenge_rating: str
    xp: int
    actions: tuple[CreatureAction, ...]
    traits: tuple[CreatureFeature, ...] = ()
    bonus_actions: tuple[CreatureFeature, ...] = ()
    reactions: tuple[CreatureFeature, ...] = ()
    damage_resistances: tuple[DamageType, ...] = ()
    damage_vulnerabilities: tuple[DamageType, ...] = ()
    damage_immunities: tuple[DamageType, ...] = ()
    condition_immunities: tuple[ConditionName, ...] = ()

    def __post_init__(self) -> None:
        if self.armor_class < 1:
            raise ValueError("armor_class must be positive")
        if self.hit_points < 1:
            raise ValueError("hit_points must be positive")
        parse_dice_notation(self.hit_dice)
        _validate_ability_scores(self.abilities)
        _validate_known_keys("saving_throws", self.saving_throws, _ABILITIES)
        _validate_known_keys("skills", self.skills, _SKILLS)
        _validate_non_negative_values("speed", self.speed)
        _validate_non_negative_values("senses", self.senses)
        if self.xp < 0:
            raise ValueError("xp cannot be negative")
        _validate_damage_types("damage_resistances", self.damage_resistances)
        _validate_damage_types("damage_vulnerabilities", self.damage_vulnerabilities)
        _validate_damage_types("damage_immunities", self.damage_immunities)
        _validate_condition_names("condition_immunities", self.condition_immunities)


@dataclass(frozen=True)
class CreatureInstance:
    """A creature definition paired with runtime hit point state."""

    id: str
    definition: CreatureDefinition
    hit_points: HitPointState


def _validate_positive_optional(name: str, value: int | None) -> None:
    if value is not None and value < 1:
        raise ValueError(f"{name} must be positive")


def _validate_ability_scores(abilities: dict[Ability, int]) -> None:
    missing = set(_ABILITIES) - set(abilities)
    if missing:
        raise ValueError(f"missing ability scores: {', '.join(sorted(missing))}")

    _validate_known_keys("abilities", abilities, _ABILITIES)

    for ability, score in abilities.items():
        if not 1 <= score <= 30:
            raise ValueError(f"{ability} ability score must be between 1 and 30")


def _validate_known_keys(name: str, values: dict[str, int], allowed: tuple[str, ...]) -> None:
    invalid = set(values) - set(allowed)
    if invalid:
        raise ValueError(f"invalid {name}: {', '.join(sorted(invalid))}")


def _validate_non_negative_values(name: str, values: dict[str, int]) -> None:
    for key, value in values.items():
        if value < 0:
            raise ValueError(f"{name}.{key} cannot be negative")


def _validate_damage_types(name: str, values: tuple[DamageType, ...]) -> None:
    invalid = set(values) - set(DAMAGE_TYPES)
    if invalid:
        raise ValueError(f"invalid {name}: {', '.join(sorted(invalid))}")


def _validate_condition_names(name: str, values: tuple[ConditionName, ...]) -> None:
    invalid = set(values) - set(CONDITION_NAMES)
    if invalid:
        raise ValueError(f"invalid {name}: {', '.join(sorted(invalid))}")


CREATURES: dict[str, CreatureDefinition] = {
    "goblin": CreatureDefinition(
        id="goblin",
        name="Goblin",
        size="small",
        type="humanoid",
        alignment="neutral evil",
        armor_class=15,
        hit_points=7,
        hit_dice="2d6",
        speed={"walk": 30},
        abilities={"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
        saving_throws={},
        skills={"stealth": 6},
        senses={"darkvision": 60, "passive_perception": 9},
        languages=("Common", "Goblin"),
        challenge_rating="1/4",
        xp=50,
        actions=(
            CreatureAction("Scimitar", 4, "1d6+2", "slashing", reach=5),
            CreatureAction("Shortbow", 4, "1d6+2", "piercing", normal_range=80, long_range=320),
        ),
        bonus_actions=(CreatureFeature("Nimble Escape", ("disengage", "hide")),),
    ),
    "cultist": CreatureDefinition(
        id="cultist",
        name="Cultist",
        size="medium",
        type="humanoid",
        alignment="any non-good alignment",
        armor_class=12,
        hit_points=9,
        hit_dice="2d8",
        speed={"walk": 30},
        abilities={"str": 11, "dex": 12, "con": 10, "int": 10, "wis": 11, "cha": 10},
        saving_throws={},
        skills={"deception": 2, "religion": 2},
        senses={"passive_perception": 10},
        languages=("any one language",),
        challenge_rating="1/8",
        xp=25,
        actions=(CreatureAction("Scimitar", 3, "1d6+1", "slashing", reach=5),),
    ),
    "bandit": CreatureDefinition(
        id="bandit",
        name="Bandit",
        size="medium",
        type="humanoid",
        alignment="any non-lawful alignment",
        armor_class=12,
        hit_points=11,
        hit_dice="2d8+2",
        speed={"walk": 30},
        abilities={"str": 11, "dex": 12, "con": 12, "int": 10, "wis": 10, "cha": 10},
        saving_throws={},
        skills={},
        senses={"passive_perception": 10},
        languages=("any one language",),
        challenge_rating="1/8",
        xp=25,
        actions=(
            CreatureAction("Scimitar", 3, "1d6+1", "slashing", reach=5),
            CreatureAction("Light Crossbow", 3, "1d8+1", "piercing", normal_range=80, long_range=320),
        ),
    ),
    "wolf": CreatureDefinition(
        id="wolf",
        name="Wolf",
        size="medium",
        type="beast",
        alignment="unaligned",
        armor_class=13,
        hit_points=11,
        hit_dice="2d8+2",
        speed={"walk": 40},
        abilities={"str": 12, "dex": 15, "con": 12, "int": 3, "wis": 12, "cha": 6},
        saving_throws={},
        skills={"perception": 3, "stealth": 4},
        senses={"passive_perception": 13},
        languages=(),
        challenge_rating="1/4",
        xp=50,
        actions=(CreatureAction("Bite", 4, "2d4+2", "piercing", reach=5),),
        traits=(
            CreatureFeature("Keen Hearing and Smell", ("perception_advantage_hearing_smell",)),
            CreatureFeature("Pack Tactics", ("attack_advantage_adjacent_ally",)),
        ),
    ),
    "skeleton": CreatureDefinition(
        id="skeleton",
        name="Skeleton",
        size="medium",
        type="undead",
        alignment="lawful evil",
        armor_class=13,
        hit_points=13,
        hit_dice="2d8+4",
        speed={"walk": 30},
        abilities={"str": 10, "dex": 14, "con": 15, "int": 6, "wis": 8, "cha": 5},
        saving_throws={},
        skills={},
        senses={"darkvision": 60, "passive_perception": 9},
        languages=("understands languages it knew in life",),
        challenge_rating="1/4",
        xp=50,
        actions=(
            CreatureAction("Shortsword", 4, "1d6+2", "piercing", reach=5),
            CreatureAction("Shortbow", 4, "1d6+2", "piercing", normal_range=80, long_range=320),
        ),
        damage_vulnerabilities=("bludgeoning",),
        damage_immunities=("poison",),
        condition_immunities=("poisoned",),
    ),
    "zombie": CreatureDefinition(
        id="zombie",
        name="Zombie",
        size="medium",
        type="undead",
        alignment="neutral evil",
        armor_class=8,
        hit_points=22,
        hit_dice="3d8+9",
        speed={"walk": 20},
        abilities={"str": 13, "dex": 6, "con": 16, "int": 3, "wis": 6, "cha": 5},
        saving_throws={"wis": 0},
        skills={},
        senses={"darkvision": 60, "passive_perception": 8},
        languages=("understands languages it knew in life",),
        challenge_rating="1/4",
        xp=50,
        actions=(CreatureAction("Slam", 3, "1d6+1", "bludgeoning", reach=5),),
        traits=(CreatureFeature("Undead Fortitude", ("drop_to_1_hp_save",)),),
        damage_immunities=("poison",),
        condition_immunities=("poisoned",),
    ),
    "ogre": CreatureDefinition(
        id="ogre",
        name="Ogre",
        size="large",
        type="giant",
        alignment="chaotic evil",
        armor_class=11,
        hit_points=59,
        hit_dice="7d10+21",
        speed={"walk": 40},
        abilities={"str": 19, "dex": 8, "con": 16, "int": 5, "wis": 7, "cha": 7},
        saving_throws={},
        skills={},
        senses={"darkvision": 60, "passive_perception": 8},
        languages=("Common", "Giant"),
        challenge_rating="2",
        xp=450,
        actions=(
            CreatureAction("Greatclub", 6, "2d8+4", "bludgeoning", reach=5),
            CreatureAction("Javelin", 6, "2d6+4", "piercing", reach=5, normal_range=30, long_range=120),
        ),
    ),
}


def creature_ability_bonus(creature: CreatureDefinition | CreatureInstance, ability: Ability) -> int:
    """Return the ability modifier for a creature definition or instance."""

    return ability_modifier(_definition(creature).abilities[ability])


def creature_skill_bonus(creature: CreatureDefinition | CreatureInstance, skill: Skill) -> int:
    """Return an explicit creature skill bonus from its stat block."""

    definition = _definition(creature)
    if skill not in definition.skills:
        raise KeyError(skill)
    return definition.skills[skill]


def creature_initiative_bonus(creature: CreatureDefinition | CreatureInstance) -> int:
    """Return a creature's initiative bonus from Dexterity."""

    return creature_ability_bonus(creature, "dex")


def create_creature_instance(
    definition: str | CreatureDefinition,
    id: str | None = None,
) -> CreatureInstance:
    """Create a creature instance with full HP from a catalog id or definition."""

    creature_definition = _resolve_definition(definition)
    return CreatureInstance(
        id=id or creature_definition.id,
        definition=creature_definition,
        hit_points=HitPointState(
            current=creature_definition.hit_points,
            maximum=creature_definition.hit_points,
        ),
    )


def creature_combatant(instance: CreatureInstance, roll: int = 0) -> dict[str, int | str]:
    """Return the legacy mapping form accepted by ``create_combat``."""

    return {
        "id": instance.id,
        "name": instance.definition.name,
        "initiative_bonus": creature_initiative_bonus(instance),
        "roll": roll,
    }


def creature_runtime_combatant(instance: CreatureInstance, roll: int = 0) -> Combatant:
    """Create a validated combatant from a creature instance."""

    return create_combatant(
        id=instance.id,
        name=instance.definition.name,
        initiative_bonus=creature_initiative_bonus(instance),
        roll=roll,
        armor_class=instance.definition.armor_class,
        hit_points=instance.hit_points,
        source=instance.definition,
    )


def creature_action_attack(
    action: CreatureAction,
    target_ac: int,
    roll: int | None = None,
    rng: RandomSource = random,
) -> AttackRollResult:
    """Resolve one creature action attack roll against a target AC."""

    return attack_roll(
        attacker_bonus=action.attack_bonus,
        target_armor_class=target_ac,
        roll=roll,
        rng=rng,
    )


def creature_action_damage(
    action: CreatureAction,
    critical: bool = False,
    rng: RandomSource = random,
) -> DamageResult:
    """Roll damage for a creature action."""

    return damage_roll(
        dice=action.damage_dice,
        type=action.damage_type,
        critical=critical,
        rng=rng,
    )


def _definition(creature: CreatureDefinition | CreatureInstance) -> CreatureDefinition:
    return creature.definition if isinstance(creature, CreatureInstance) else creature


def _resolve_definition(definition: str | CreatureDefinition) -> CreatureDefinition:
    if isinstance(definition, CreatureDefinition):
        return definition
    return CREATURES[definition]
