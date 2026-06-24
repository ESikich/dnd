from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from random import random
from typing import Any, Literal, TypeVar

from dnd5e.abilities import RandomSource, proficiency_bonus, random_die
from dnd5e.combat import DamageResult, damage_roll
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

    def __post_init__(self) -> None:
        _validate_id_and_name(self.id, self.name)
        for tag in self.tags:
            if not tag:
                raise ValueError("feature tags cannot be empty")


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
                tags=tuple(_string_list_field(entry, "tags", "feature")),
                resource=_resource_definition_field(entry, "resource", "feature"),
            )
            for entry in _validated_entries(
                entries,
                "features",
                {"id", "name", "tags", "resource"},
            )
        ],
    )


def _resource_definition_field(
    entry: Mapping[str, Any], name: str, section: str
) -> ResourceDefinition | None:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
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


_BUILTIN_FEATURES = load_builtin_feature_pack()
FEATURES: dict[str, FeatureDefinition] = _BUILTIN_FEATURES.features
