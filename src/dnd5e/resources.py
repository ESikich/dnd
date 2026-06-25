from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from random import random
from typing import Any, Literal, TypeVar

from dnd5e.abilities import RandomSource, proficiency_bonus, random_die
from dnd5e.combat import DamageResult, damage_roll
from dnd5e.effects import RollModifier
from dnd5e.hit_points import HealingResult, HitPointState, apply_healing
from dnd5e.types import DamageType

ResourceRefresh = Literal["none", "short_rest", "long_rest", "recharge"]
T = TypeVar("T")


@dataclass(frozen=True)
class ResourceDefinition:
    """Limited-use resource metadata for charges, rests, proficiency uses, or recharge."""

    id: str
    name: str
    maximum: int | None = None
    refresh: ResourceRefresh = "long_rest"
    proficiency_based: bool = False
    recharge_minimum: int | None = None
    recharge_die: int = 6

    def __post_init__(self) -> None:
        _validate_id_and_name(self.id, self.name)
        if self.maximum is None and not self.proficiency_based:
            raise ValueError("maximum is required unless proficiency_based is true")
        if self.maximum is not None:
            _validate_positive("maximum", self.maximum)
        if self.refresh not in RESOURCE_REFRESHES:
            raise ValueError(f"unknown resource refresh: {self.refresh}")
        if self.recharge_minimum is not None:
            if self.refresh != "recharge":
                raise ValueError("recharge_minimum requires recharge refresh")
            if not 1 <= self.recharge_minimum <= self.recharge_die:
                raise ValueError("recharge_minimum must be from 1 to recharge_die")
        if self.refresh == "recharge" and self.recharge_minimum is None:
            raise ValueError("recharge refresh requires recharge_minimum")
        _validate_positive("recharge_die", self.recharge_die)


@dataclass(frozen=True)
class ResourceState:
    """Runtime remaining uses for a limited-use resource."""

    definition: ResourceDefinition
    maximum: int
    remaining: int

    def __post_init__(self) -> None:
        _validate_positive("maximum", self.maximum)
        if not 0 <= self.remaining <= self.maximum:
            raise ValueError("remaining must be from 0 to maximum")


@dataclass(frozen=True)
class RechargeResult:
    """Result of a recharge roll for a limited-use resource."""

    state: ResourceState
    roll: int
    recharged: bool

    def __post_init__(self) -> None:
        if not 1 <= self.roll <= self.state.definition.recharge_die:
            raise ValueError("recharge roll must be within the recharge die")


@dataclass(frozen=True)
class FeatureDefinition:
    """Named class, creature, or rules feature with optional limited-use state."""

    id: str
    name: str
    tags: tuple[str, ...] = ()
    resource: ResourceDefinition | None = None
    source_type: str = "feature"
    level: int | None = None
    class_id: str | None = None
    subclass_id: str | None = None
    parent_id: str | None = None
    race_ids: tuple[str, ...] = ()
    prerequisite_ids: tuple[str, ...] = ()
    prerequisite_abilities: dict[str, int] = field(default_factory=dict)
    effects: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id_and_name(self.id, self.name)
        for tag in self.tags:
            if not tag:
                raise ValueError("feature tags cannot be empty")
        if not self.source_type:
            raise ValueError("feature source type is required")
        if self.level is not None and self.level < 1:
            raise ValueError("feature level must be positive")
        if self.class_id == "":
            raise ValueError("feature class id cannot be empty")
        if self.subclass_id == "":
            raise ValueError("feature subclass id cannot be empty")
        if self.parent_id == "":
            raise ValueError("feature parent id cannot be empty")
        for race_id in self.race_ids:
            if not race_id:
                raise ValueError("feature race id cannot be empty")
        for prerequisite_id in self.prerequisite_ids:
            if not prerequisite_id:
                raise ValueError("feature prerequisite id cannot be empty")
        for ability, score in self.prerequisite_abilities.items():
            if not ability:
                raise ValueError("feature prerequisite ability cannot be empty")
            if score < 1:
                raise ValueError("feature prerequisite ability score must be positive")
        for effect in self.effects:
            if not effect:
                raise ValueError("feature effect cannot be empty")
        if self.source_url == "":
            raise ValueError("feature source URL cannot be empty")


@dataclass(frozen=True)
class FeaturePack:
    """Loaded feature content grouped into a feature-definition catalog."""

    features: dict[str, FeatureDefinition]


@dataclass(frozen=True)
class FeatureState:
    """Runtime state for a feature and its optional resource."""

    definition: FeatureDefinition
    resource: ResourceState | None = None

    def __post_init__(self) -> None:
        if self.definition.resource is None and self.resource is not None:
            raise ValueError("resource state requires a feature resource definition")
        if (
            self.definition.resource is not None
            and self.resource is not None
            and self.definition.resource.id != self.resource.definition.id
        ):
            raise ValueError("resource state does not match feature resource definition")


@dataclass(frozen=True)
class SecondWindResult:
    """Healing and feature state produced by using Second Wind."""

    feature: FeatureState
    healing: HealingResult
    roll: int

    def __post_init__(self) -> None:
        if self.feature.definition.id != "second_wind":
            raise ValueError("Second Wind result requires the Second Wind feature")
        if not 1 <= self.roll <= 10:
            raise ValueError("Second Wind roll must be from 1 to 10")


@dataclass(frozen=True)
class BreathWeaponProfile:
    """Level-scaled breath weapon damage and save DC metadata."""

    damage_dice: str
    save_dc: int

    def __post_init__(self) -> None:
        if self.save_dc < 1:
            raise ValueError("breath weapon save DC must be positive")


RESOURCE_REFRESHES: tuple[ResourceRefresh, ...] = (
    "none",
    "short_rest",
    "long_rest",
    "recharge",
)


def load_feature_pack(path: str | Path) -> FeaturePack:
    """Load feature definitions from a feature content-pack JSON file."""

    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("feature content pack must be a JSON object")
    return load_feature_pack_data(data)


def load_builtin_feature_pack() -> FeaturePack:
    """Load the packaged SRD-style feature content pack."""

    data_resource = files("dnd5e.data").joinpath("features.json")
    with data_resource.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("built-in feature content pack must be a JSON object")
    return load_feature_pack_data(data)


def load_feature_pack_data(data: Mapping[str, Any]) -> FeaturePack:
    """Validate and construct a feature pack from decoded JSON-style data."""

    _validate_pack_keys(data)
    return FeaturePack(features=_load_feature_entries(data["features"]))


def _validate_pack_keys(data: Mapping[str, Any]) -> None:
    expected = {"features"}
    missing = expected - set(data)
    if missing:
        raise ValueError(f"feature content pack missing sections: {', '.join(sorted(missing))}")
    extra = set(data) - expected
    if extra:
        raise ValueError(f"feature content pack has unknown sections: {', '.join(sorted(extra))}")


def _load_feature_entries(entries: Any) -> dict[str, FeatureDefinition]:
    return _catalog_by_id(
        "feature",
        [
            FeatureDefinition(
                id=_field(entry, "id", str, "feature"),
                name=_field(entry, "name", str, "feature"),
                tags=tuple(_optional_string_list_field(entry, "tags", "feature")),
                resource=_optional_resource_definition_field(entry, "resource", "feature"),
                source_type=_optional_missing_field(entry, "source_type", str, "feature") or "feature",
                level=_optional_missing_field(entry, "level", int, "feature"),
                class_id=_optional_missing_field(entry, "class_id", str, "feature"),
                subclass_id=_optional_missing_field(entry, "subclass_id", str, "feature"),
                parent_id=_optional_missing_field(entry, "parent_id", str, "feature"),
                race_ids=_optional_string_list_field(entry, "race_ids", "feature"),
                prerequisite_ids=_optional_string_list_field(
                    entry, "prerequisite_ids", "feature"
                ),
                prerequisite_abilities=dict(
                    _optional_int_mapping_field(entry, "prerequisite_abilities", "feature")
                ),
                effects=_optional_string_list_field(entry, "effects", "feature"),
                source_url=_optional_missing_field(entry, "source_url", str, "feature"),
            )
            for entry in _validated_entries(
                entries,
                "features",
                {
                    "id",
                    "name",
                    "tags",
                    "resource",
                    "source_type",
                    "level",
                    "class_id",
                    "subclass_id",
                    "parent_id",
                    "race_ids",
                    "prerequisite_ids",
                    "prerequisite_abilities",
                    "effects",
                    "source_url",
                },
            )
        ],
    )


def _optional_resource_definition_field(
    entry: Mapping[str, Any], name: str, section: str
) -> ResourceDefinition | None:
    if name not in entry:
        return None
    value = entry[name]
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"{section}.{name} must be an object or null")
    return ResourceDefinition(
        id=_field(value, "id", str, "resource"),
        name=_field(value, "name", str, "resource"),
        maximum=_optional_field(value, "maximum", int, "resource"),
        refresh=_field(value, "refresh", str, "resource"),  # type: ignore[arg-type]
        proficiency_based=_field(value, "proficiency_based", bool, "resource"),
        recharge_minimum=_optional_field(value, "recharge_minimum", int, "resource"),
        recharge_die=_field(value, "recharge_die", int, "resource"),
    )


def _validated_entries(
    entries: Any, section: str, expected_fields: set[str]
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(entries, list):
        raise ValueError(f"feature content section {section} must be a list")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError(f"feature content section {section} entries must be objects")
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


def _field(entry: Mapping[str, Any], name: str, expected_type: type[T], section: str) -> T:
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


def _optional_missing_field(
    entry: Mapping[str, Any],
    name: str,
    expected_type: type[T],
    section: str,
) -> T | None:
    if name not in entry:
        return None
    return _optional_field(entry, name, expected_type, section)


def _optional_string_list_field(
    entry: Mapping[str, Any], name: str, section: str
) -> tuple[str, ...]:
    if name not in entry:
        return ()
    return _string_list_field(entry, name, section)


def _optional_int_mapping_field(
    entry: Mapping[str, Any], name: str, section: str
) -> dict[str, int]:
    if name not in entry:
        return {}
    value = entry[name]
    if not isinstance(value, Mapping):
        raise ValueError(f"{section}.{name} must be an object")
    result: dict[str, int] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{section}.{name} keys must be strings")
        if not isinstance(item, int):
            raise ValueError(f"{section}.{name}.{key} must be int")
        result[key] = item
    return result


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


def create_resource_state(
    definition: ResourceDefinition,
    *,
    level: int | None = None,
    remaining: int | None = None,
) -> ResourceState:
    """Create runtime resource state, resolving proficiency-based maximums if needed."""

    maximum = resource_maximum(definition, level=level)
    return ResourceState(
        definition=definition,
        maximum=maximum,
        remaining=maximum if remaining is None else remaining,
    )


def resource_maximum(definition: ResourceDefinition, *, level: int | None = None) -> int:
    """Return a resource maximum from fixed charges or proficiency bonus."""

    if definition.proficiency_based:
        if level is None:
            raise ValueError("level is required for proficiency-based resources")
        return proficiency_bonus(level)
    if definition.maximum is None:
        raise ValueError("resource maximum is not configured")
    return definition.maximum


def spend_resource(state: ResourceState, amount: int = 1) -> ResourceState:
    """Spend limited-use resource charges and return updated state."""

    _validate_positive("amount", amount)
    if state.remaining < amount:
        raise ValueError(f"not enough {state.definition.name} remaining")
    return ResourceState(
        definition=state.definition,
        maximum=state.maximum,
        remaining=state.remaining - amount,
    )


def restore_resource(state: ResourceState) -> ResourceState:
    """Restore a resource to its maximum uses."""

    return ResourceState(
        definition=state.definition,
        maximum=state.maximum,
        remaining=state.maximum,
    )


def short_rest_resource(state: ResourceState) -> ResourceState:
    """Refresh resources that recover on a short rest."""

    if state.definition.refresh == "short_rest":
        return restore_resource(state)
    return state


def long_rest_resource(state: ResourceState) -> ResourceState:
    """Refresh resources that recover on either a short or long rest."""

    if state.definition.refresh in ("short_rest", "long_rest"):
        return restore_resource(state)
    return state


def recharge_resource(
    state: ResourceState,
    *,
    roll: int | None = None,
    rng: RandomSource = random,
) -> RechargeResult:
    """Roll a recharge resource and restore it on a successful recharge roll."""

    if state.definition.refresh != "recharge" or state.definition.recharge_minimum is None:
        raise ValueError("resource does not use recharge")
    result_roll = roll if roll is not None else int(rng() * state.definition.recharge_die) + 1
    if not 1 <= result_roll <= state.definition.recharge_die:
        raise ValueError("recharge roll must be within the recharge die")
    recharged = result_roll >= state.definition.recharge_minimum
    return RechargeResult(
        state=restore_resource(state) if recharged else state,
        roll=result_roll,
        recharged=recharged,
    )


def create_feature_state(
    definition: FeatureDefinition,
    *,
    level: int | None = None,
    remaining: int | None = None,
) -> FeatureState:
    """Create feature state, including resource state when the feature has uses."""

    resource = None
    if definition.resource is not None:
        resource = create_resource_state(definition.resource, level=level, remaining=remaining)
    return FeatureState(definition=definition, resource=resource)


def spend_feature_resource(state: FeatureState, amount: int = 1) -> FeatureState:
    """Spend a feature's resource uses and return updated feature state."""

    if state.resource is None:
        raise ValueError(f"{state.definition.name} has no limited-use resource")
    return FeatureState(
        definition=state.definition,
        resource=spend_resource(state.resource, amount),
    )


def short_rest_feature(state: FeatureState) -> FeatureState:
    """Refresh a feature's resource if it recovers on a short rest."""

    if state.resource is None:
        return state
    return FeatureState(
        definition=state.definition,
        resource=short_rest_resource(state.resource),
    )


def long_rest_feature(state: FeatureState) -> FeatureState:
    """Refresh a feature's resource if it recovers on a rest."""

    if state.resource is None:
        return state
    return FeatureState(
        definition=state.definition,
        resource=long_rest_resource(state.resource),
    )


def recharge_feature(
    state: FeatureState,
    *,
    roll: int | None = None,
    rng: RandomSource = random,
) -> tuple[FeatureState, RechargeResult]:
    """Roll recharge for a feature resource and return updated feature state."""

    if state.resource is None:
        raise ValueError(f"{state.definition.name} has no limited-use resource")
    result = recharge_resource(state.resource, roll=roll, rng=rng)
    return FeatureState(definition=state.definition, resource=result.state), result


def feature_armor_class_bonus(
    features: tuple[FeatureDefinition | str, ...],
    *,
    wearing_armor: bool = True,
) -> int:
    """Return flat AC bonus from active feature metadata."""

    if not wearing_armor:
        return 0
    return sum(1 for feature in _resolve_features(features) if "armor_class_bonus" in feature.effects)


def feature_rage_damage_bonus(
    features: tuple[FeatureDefinition | str, ...],
    *,
    barbarian_level: int,
    melee_weapon_attack: bool = True,
    using_strength: bool = True,
) -> int:
    """Return the Rage melee Strength damage bonus for a barbarian level."""

    if barbarian_level < 1:
        raise ValueError("barbarian level must be positive")
    if not melee_weapon_attack or not using_strength:
        return 0
    if not any("rage_damage_bonus" in feature.effects for feature in _resolve_features(features)):
        return 0
    if barbarian_level >= 16:
        return 4
    if barbarian_level >= 9:
        return 3
    return 2


def feature_damage_resistances(features: tuple[FeatureDefinition | str, ...]) -> tuple[DamageType, ...]:
    """Return damage resistances contributed by active feature metadata."""

    resistances: set[DamageType] = set()
    for feature in _resolve_features(features):
        if "rage_resistance" in feature.effects:
            resistances.update(("bludgeoning", "piercing", "slashing"))
    return tuple(sorted(resistances))


def feature_ability_check_modifier(
    features: tuple[FeatureDefinition | str, ...],
    ability: str,
) -> RollModifier:
    """Return advantage metadata from active features for an ability check."""

    if ability == "str" and any("strength_advantage" in feature.effects for feature in _resolve_features(features)):
        return RollModifier(advantage="advantage", reasons=("feature",))
    return RollModifier()


def feature_saving_throw_modifier(
    features: tuple[FeatureDefinition | str, ...],
    ability: str,
) -> RollModifier:
    """Return advantage metadata from active features for a saving throw."""

    if ability == "str" and any("strength_advantage" in feature.effects for feature in _resolve_features(features)):
        return RollModifier(advantage="advantage", reasons=("feature",))
    return RollModifier()


def feature_attack_modifier(
    features: tuple[FeatureDefinition | str, ...],
    *,
    target_grappled_by_you: bool = False,
) -> RollModifier:
    """Return attack advantage metadata from active feature effects."""

    if target_grappled_by_you and any(
        "grapple_attack_advantage" in feature.effects for feature in _resolve_features(features)
    ):
        return RollModifier(advantage="advantage", reasons=("feature",))
    return RollModifier()


def feature_has_darkvision(features: tuple[FeatureDefinition | str, ...]) -> bool:
    """Return whether active feature metadata grants darkvision."""

    return any("darkvision" in feature.effects for feature in _resolve_features(features))


def breath_weapon_profile(level: int, constitution_modifier: int, proficiency: int) -> BreathWeaponProfile:
    """Return dragonborn breath weapon damage dice and save DC for a character level."""

    if level < 1:
        raise ValueError("level must be positive")
    dice = "2d6"
    if level >= 16:
        dice = "5d6"
    elif level >= 11:
        dice = "4d6"
    elif level >= 6:
        dice = "3d6"
    return BreathWeaponProfile(
        damage_dice=dice,
        save_dc=8 + constitution_modifier + proficiency,
    )


def feature_prerequisites_met(
    feature: FeatureDefinition | str,
    *,
    abilities: Mapping[str, int],
) -> bool:
    """Return whether ability-score prerequisites for a feature are met."""

    definition = _resolve_feature(feature)
    return all(
        abilities.get(ability, 0) >= score
        for ability, score in definition.prerequisite_abilities.items()
    )


def apply_second_wind(
    state: FeatureState,
    hit_points: HitPointState,
    *,
    fighter_level: int,
    roll: int | None = None,
    rng: RandomSource = random,
) -> SecondWindResult:
    """Spend Second Wind and heal ``1d10 + fighter_level`` hit points."""

    if state.definition.id != "second_wind":
        raise ValueError("feature must be Second Wind")
    if not 1 <= fighter_level <= 20:
        raise ValueError("fighter_level must be from 1 to 20")

    spent = spend_feature_resource(state)
    die_roll = _roll_feature_die(10, roll=roll, rng=rng, context="Second Wind roll")
    healing = apply_healing(hit_points, die_roll + fighter_level)
    return SecondWindResult(feature=spent, healing=healing, roll=die_roll)


def sneak_attack_damage_dice(rogue_level: int) -> str:
    """Return Sneak Attack bonus damage dice for a rogue level."""

    if not 1 <= rogue_level <= 20:
        raise ValueError("rogue_level must be from 1 to 20")
    return f"{(rogue_level + 1) // 2}d6"


def sneak_attack_damage(
    *,
    rogue_level: int,
    damage_type: DamageType,
    critical: bool = False,
    rng: RandomSource = random,
) -> DamageResult:
    """Roll Sneak Attack bonus damage using the triggering attack's damage type."""

    return damage_roll(
        dice=sneak_attack_damage_dice(rogue_level),
        type=damage_type,
        critical=critical,
        rng=rng,
    )


def _validate_id_and_name(id: str, name: str) -> None:
    if not id:
        raise ValueError("id is required")
    if not name:
        raise ValueError("name is required")


def _validate_positive(name: str, value: int) -> None:
    if value < 1:
        raise ValueError(f"{name} must be positive")


def _roll_feature_die(
    sides: int,
    *,
    roll: int | None,
    rng: RandomSource,
    context: str,
) -> int:
    if roll is not None:
        if not 1 <= roll <= sides:
            raise ValueError(f"{context} must be from 1 to {sides}")
        return roll
    return random_die(sides, rng)


def _resolve_features(features: tuple[FeatureDefinition | str, ...]) -> tuple[FeatureDefinition, ...]:
    return tuple(_resolve_feature(feature) for feature in features)


def _resolve_feature(feature: FeatureDefinition | str) -> FeatureDefinition:
    if isinstance(feature, FeatureDefinition):
        return feature
    return FEATURES[feature]


_BUILTIN_FEATURES = load_builtin_feature_pack()
FEATURES: dict[str, FeatureDefinition] = _BUILTIN_FEATURES.features
