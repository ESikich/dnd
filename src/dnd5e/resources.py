from __future__ import annotations

from dataclasses import dataclass
from random import random
from typing import Literal

from dnd5e.abilities import RandomSource, proficiency_bonus

ResourceRefresh = Literal["none", "short_rest", "long_rest", "recharge"]


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


RESOURCE_REFRESHES: tuple[ResourceRefresh, ...] = (
    "none",
    "short_rest",
    "long_rest",
    "recharge",
)


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


def _validate_id_and_name(id: str, name: str) -> None:
    if not id:
        raise ValueError("id is required")
    if not name:
        raise ValueError("name is required")


def _validate_positive(name: str, value: int) -> None:
    if value < 1:
        raise ValueError(f"{name} must be positive")


FEATURES: dict[str, FeatureDefinition] = {
    "second_wind": FeatureDefinition(
        id="second_wind",
        name="Second Wind",
        tags=("healing",),
        resource=ResourceDefinition(
            id="second_wind",
            name="Second Wind",
            maximum=1,
            refresh="short_rest",
        ),
    ),
    "rage": FeatureDefinition(
        id="rage",
        name="Rage",
        tags=("damage_bonus", "resistance"),
        resource=ResourceDefinition(
            id="rage",
            name="Rage",
            maximum=2,
            refresh="long_rest",
        ),
    ),
    "sneak_attack": FeatureDefinition(
        id="sneak_attack",
        name="Sneak Attack",
        tags=("bonus_damage", "once_per_turn"),
    ),
    "pack_tactics": FeatureDefinition(
        id="pack_tactics",
        name="Pack Tactics",
        tags=("attack_advantage_adjacent_ally",),
    ),
    "proficiency_uses": FeatureDefinition(
        id="proficiency_uses",
        name="Proficiency Uses",
        tags=("proficiency_based_uses",),
        resource=ResourceDefinition(
            id="proficiency_uses",
            name="Proficiency Uses",
            refresh="long_rest",
            proficiency_based=True,
        ),
    ),
    "recharge_5_6": FeatureDefinition(
        id="recharge_5_6",
        name="Recharge 5-6",
        tags=("recharge",),
        resource=ResourceDefinition(
            id="recharge_5_6",
            name="Recharge 5-6",
            maximum=1,
            refresh="recharge",
            recharge_minimum=5,
        ),
    ),
}
