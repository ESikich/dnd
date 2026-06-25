from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from random import random
from typing import Any, TypeVar

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
from dnd5e.resources import FeatureDefinition, FeatureState, ResourceDefinition, create_feature_state
from dnd5e.skills import SKILL_ABILITIES
from dnd5e.types import Ability, ConditionName, CreatureSize, CreatureType, DamageType, Skill

_ABILITIES: tuple[Ability, ...] = ("str", "dex", "con", "int", "wis", "cha")
_SKILLS: tuple[Skill, ...] = tuple(SKILL_ABILITIES)
_KnownKey = TypeVar("_KnownKey", bound=str)
T = TypeVar("T")


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
    damage_dice: str | None = None
    damage_type: DamageType | None = None
    reach: int | None = None
    normal_range: int | None = None
    long_range: int | None = None
    target: str = "one target"
    recharge_minimum: int | None = None
    recharge_die: int = 6

    def __post_init__(self) -> None:
        if (self.damage_dice is None) != (self.damage_type is None):
            raise ValueError("damage_dice and damage_type must be provided together")
        if self.damage_dice is not None:
            parse_dice_notation(self.damage_dice)
        _validate_positive_optional("reach", self.reach)
        _validate_positive_optional("normal_range", self.normal_range)
        _validate_positive_optional("long_range", self.long_range)
        _validate_positive_optional("recharge_die", self.recharge_die)
        if self.normal_range is not None and self.long_range is not None and self.long_range < self.normal_range:
            raise ValueError("long_range must be greater than or equal to normal_range")
        if self.recharge_minimum is not None and not 1 <= self.recharge_minimum <= self.recharge_die:
            raise ValueError("recharge_minimum must be from 1 to recharge_die")


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
    subtype: str | None = None
    armor_desc: str | None = None
    proficiency_bonus: int | None = None
    legendary_actions: tuple[CreatureFeature, ...] = ()
    damage_resistance_notes: tuple[str, ...] = ()
    damage_vulnerability_notes: tuple[str, ...] = ()
    damage_immunity_notes: tuple[str, ...] = ()
    image_url: str | None = None
    source_url: str | None = None

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
        _validate_positive_optional("proficiency_bonus", self.proficiency_bonus)


@dataclass(frozen=True)
class CreaturePack:
    """Loaded creature content grouped into a creature-definition catalog."""

    creatures: dict[str, CreatureDefinition]


@dataclass(frozen=True)
class CreatureInstance:
    """A creature definition paired with runtime hit point state."""

    id: str
    definition: CreatureDefinition
    hit_points: HitPointState


def load_creature_pack(path: str | Path) -> CreaturePack:
    """Load creature definitions from a creature content-pack JSON file."""

    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("creature content pack must be a JSON object")
    return load_creature_pack_data(data)


def load_builtin_creature_pack() -> CreaturePack:
    """Load the packaged SRD-style creature content pack."""

    data_resource = files("dnd5e.data").joinpath("creatures.json")
    with data_resource.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("built-in creature content pack must be a JSON object")
    return load_creature_pack_data(data)


def load_creature_pack_data(data: Mapping[str, Any]) -> CreaturePack:
    """Validate and construct a creature pack from decoded JSON-style data."""

    _validate_pack_keys(data)
    return CreaturePack(creatures=_load_creature_entries(data["creatures"]))


def _validate_pack_keys(data: Mapping[str, Any]) -> None:
    expected = {"creatures"}
    missing = expected - set(data)
    if missing:
        raise ValueError(f"creature content pack missing sections: {', '.join(sorted(missing))}")
    extra = set(data) - expected
    if extra:
        raise ValueError(f"creature content pack has unknown sections: {', '.join(sorted(extra))}")


def _load_creature_entries(entries: Any) -> dict[str, CreatureDefinition]:
    return _catalog_by_id(
        [
            CreatureDefinition(
                id=_field(entry, "id", str, "creature"),
                name=_field(entry, "name", str, "creature"),
                size=_field(entry, "size", str, "creature"),  # type: ignore[arg-type]
                type=_field(entry, "type", str, "creature"),  # type: ignore[arg-type]
                alignment=_field(entry, "alignment", str, "creature"),
                armor_class=_field(entry, "armor_class", int, "creature"),
                hit_points=_field(entry, "hit_points", int, "creature"),
                hit_dice=_field(entry, "hit_dice", str, "creature"),
                speed=dict(_int_mapping_field(entry, "speed", "creature")),
                abilities=dict(_int_mapping_field(entry, "abilities", "creature")),  # type: ignore[arg-type]
                saving_throws=dict(_int_mapping_field(entry, "saving_throws", "creature")),  # type: ignore[arg-type]
                skills=dict(_int_mapping_field(entry, "skills", "creature")),  # type: ignore[arg-type]
                senses=dict(_int_mapping_field(entry, "senses", "creature")),
                languages=_string_tuple_field(entry, "languages", "creature"),
                challenge_rating=_field(entry, "challenge_rating", str, "creature"),
                xp=_field(entry, "xp", int, "creature"),
                actions=tuple(_action_entries(entry, "actions", "creature")),
                traits=tuple(_feature_entries(entry, "traits", "creature")),
                bonus_actions=tuple(_feature_entries(entry, "bonus_actions", "creature")),
                reactions=tuple(_feature_entries(entry, "reactions", "creature")),
                damage_resistances=_string_tuple_field(entry, "damage_resistances", "creature"),  # type: ignore[arg-type]
                damage_vulnerabilities=_string_tuple_field(entry, "damage_vulnerabilities", "creature"),  # type: ignore[arg-type]
                damage_immunities=_string_tuple_field(entry, "damage_immunities", "creature"),  # type: ignore[arg-type]
                condition_immunities=_string_tuple_field(entry, "condition_immunities", "creature"),  # type: ignore[arg-type]
                subtype=_optional_default_field(entry, "subtype", str, "creature"),
                armor_desc=_optional_default_field(entry, "armor_desc", str, "creature"),
                proficiency_bonus=_optional_default_field(entry, "proficiency_bonus", int, "creature"),
                legendary_actions=tuple(
                    _feature_entries(entry, "legendary_actions", "creature", required=False)
                ),
                damage_resistance_notes=_string_tuple_default_field(entry, "damage_resistance_notes", "creature"),
                damage_vulnerability_notes=_string_tuple_default_field(entry, "damage_vulnerability_notes", "creature"),
                damage_immunity_notes=_string_tuple_default_field(entry, "damage_immunity_notes", "creature"),
                image_url=_optional_default_field(entry, "image_url", str, "creature"),
                source_url=_optional_default_field(entry, "source_url", str, "creature"),
            )
            for entry in _validated_entries(
                entries,
                "creatures",
                {
                    "id",
                    "name",
                    "size",
                    "type",
                    "alignment",
                    "armor_class",
                    "hit_points",
                    "hit_dice",
                    "speed",
                    "abilities",
                    "saving_throws",
                    "skills",
                    "senses",
                    "languages",
                    "challenge_rating",
                    "xp",
                    "actions",
                    "traits",
                    "bonus_actions",
                    "reactions",
                    "damage_resistances",
                    "damage_vulnerabilities",
                    "damage_immunities",
                    "condition_immunities",
                    "subtype",
                    "armor_desc",
                    "proficiency_bonus",
                    "legendary_actions",
                    "damage_resistance_notes",
                    "damage_vulnerability_notes",
                    "damage_immunity_notes",
                    "image_url",
                    "source_url",
                },
            )
        ]
    )


def _action_entries(
    entry: Mapping[str, Any],
    name: str,
    section: str,
) -> tuple[CreatureAction, ...]:
    return tuple(
        CreatureAction(
            name=_field(action, "name", str, "creature action"),
            attack_bonus=_field(action, "attack_bonus", int, "creature action"),
            damage_dice=_optional_field(action, "damage_dice", str, "creature action"),
            damage_type=_optional_field(action, "damage_type", str, "creature action"),  # type: ignore[arg-type]
            reach=_optional_field(action, "reach", int, "creature action"),
            normal_range=_optional_field(action, "normal_range", int, "creature action"),
            long_range=_optional_field(action, "long_range", int, "creature action"),
            target=_field(action, "target", str, "creature action"),
            recharge_minimum=_optional_field(action, "recharge_minimum", int, "creature action"),
            recharge_die=_field(action, "recharge_die", int, "creature action"),
        )
        for action in _validated_nested_entries(
            entry,
            name,
            section,
            {
                "name",
                "attack_bonus",
                "damage_dice",
                "damage_type",
                "reach",
                "normal_range",
                "long_range",
                "target",
                "recharge_minimum",
                "recharge_die",
            },
        )
    )


def _feature_entries(
    entry: Mapping[str, Any],
    name: str,
    section: str,
    *,
    required: bool = True,
) -> tuple[CreatureFeature, ...]:
    if not required and name not in entry:
        return ()
    return tuple(
        CreatureFeature(
            name=_field(feature, "name", str, "creature feature"),
            tags=_string_tuple_field(feature, "tags", "creature feature"),
        )
        for feature in _validated_nested_entries(entry, name, section, {"name", "tags"})
    )


def _validated_entries(
    entries: Any, section: str, expected_fields: set[str]
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(entries, list):
        raise ValueError(f"creature content section {section} must be a list")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError(f"creature content section {section} entries must be objects")
        extra = set(entry) - expected_fields
        if extra:
            raise ValueError(f"{section} entry has unknown fields: {', '.join(sorted(extra))}")
    return tuple(entries)


def _validated_nested_entries(
    entry: Mapping[str, Any],
    name: str,
    section: str,
    expected_fields: set[str],
) -> tuple[Mapping[str, Any], ...]:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, list):
        raise ValueError(f"{section}.{name} must be a list")
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"{section}.{name} entries must be objects")
        extra = set(item) - expected_fields
        if extra:
            raise ValueError(f"{section}.{name} entry has unknown fields: {', '.join(sorted(extra))}")
    return tuple(value)


def _catalog_by_id(entries: list[CreatureDefinition]) -> dict[str, CreatureDefinition]:
    catalog: dict[str, CreatureDefinition] = {}
    for entry in entries:
        if entry.id in catalog:
            raise ValueError(f"duplicate creature id: {entry.id}")
        catalog[entry.id] = entry
    return catalog


def _field(entry: Mapping[str, Any], name: str, expected_type: type[T], section: str) -> T:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__}")
    return value


def _optional_field(
    entry: Mapping[str, Any],
    name: str,
    expected_type: type[T],
    section: str,
) -> T | None:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if value is None:
        return None
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__} or null")
    return value


def _optional_default_field(
    entry: Mapping[str, Any],
    name: str,
    expected_type: type[T],
    section: str,
) -> T | None:
    if name not in entry:
        return None
    value = entry[name]
    if value is None:
        return None
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__} or null")
    return value


def _string_tuple_field(entry: Mapping[str, Any], name: str, section: str) -> tuple[str, ...]:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, list):
        raise ValueError(f"{section}.{name} must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{section}.{name} entries must be strings")
    return tuple(value)


def _string_tuple_default_field(entry: Mapping[str, Any], name: str, section: str) -> tuple[str, ...]:
    if name not in entry:
        return ()
    return _string_tuple_field(entry, name, section)


def _int_mapping_field(entry: Mapping[str, Any], name: str, section: str) -> dict[str, int]:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, Mapping):
        raise ValueError(f"{section}.{name} must be an object")
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{section}.{name} keys must be strings")
        if not isinstance(item, int):
            raise ValueError(f"{section}.{name}.{key} must be int")
    return dict(value)


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


def _validate_known_keys(
    name: str,
    values: Mapping[_KnownKey, int],
    allowed: tuple[_KnownKey, ...],
) -> None:
    invalid = set(values) - set(allowed)
    if invalid:
        raise ValueError(f"invalid {name}: {', '.join(sorted(invalid))}")


def _validate_non_negative_values(name: str, values: Mapping[str, int]) -> None:
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


_BUILTIN_CREATURES = load_builtin_creature_pack()
CREATURES: dict[str, CreatureDefinition] = _BUILTIN_CREATURES.creatures


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

    if action.damage_dice is None or action.damage_type is None:
        raise ValueError(f"{action.name} does not deal direct damage")
    return damage_roll(
        dice=action.damage_dice,
        type=action.damage_type,
        critical=critical,
        rng=rng,
    )


def creature_action_recharge_feature(action: CreatureAction) -> FeatureDefinition:
    """Create limited-use feature metadata for a rechargeable creature action."""

    if action.recharge_minimum is None:
        raise ValueError(f"{action.name} does not use recharge")
    return FeatureDefinition(
        id=f"{_rules_id(action.name)}_recharge",
        name=f"{action.name} Recharge",
        tags=("recharge", "creature_action"),
        resource=ResourceDefinition(
            id=f"{_rules_id(action.name)}_recharge",
            name=f"{action.name} Recharge",
            maximum=1,
            refresh="recharge",
            recharge_minimum=action.recharge_minimum,
            recharge_die=action.recharge_die,
        ),
    )


def creature_action_recharge_state(
    action: CreatureAction,
    *,
    remaining: int | None = None,
) -> FeatureState:
    """Create runtime feature state for a rechargeable creature action."""

    return create_feature_state(
        creature_action_recharge_feature(action),
        remaining=remaining,
    )


def _definition(creature: CreatureDefinition | CreatureInstance) -> CreatureDefinition:
    return creature.definition if isinstance(creature, CreatureInstance) else creature


def _resolve_definition(definition: str | CreatureDefinition) -> CreatureDefinition:
    if isinstance(definition, CreatureDefinition):
        return definition
    return CREATURES[definition]


def _rules_id(value: str) -> str:
    return "_".join(value.lower().replace("-", " ").split())
