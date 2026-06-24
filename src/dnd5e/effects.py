from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dnd5e.types import Ability, AdvantageState, ConditionName, DamageType


@dataclass(frozen=True)
class RollModifier:
    """Advantage or disadvantage contributed by reusable effect hooks."""

    advantage: AdvantageState = "normal"
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class DamageAdjustmentResult:
    """Damage amount after vulnerability, resistance, or immunity is applied."""

    original: int
    adjusted: int
    damage_type: DamageType
    modifiers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.original < 0:
            raise ValueError("original damage cannot be negative")
        if self.adjusted < 0:
            raise ValueError("adjusted damage cannot be negative")


def combine_advantage(left: AdvantageState, right: AdvantageState) -> AdvantageState:
    """Combine two advantage states using normal cancellation rules."""

    if left == "normal":
        return right
    if right == "normal" or left == right:
        return left
    return "normal"


def condition_attack_modifier(
    *,
    attacker_conditions: tuple[ConditionName, ...] = (),
    target_conditions: tuple[ConditionName, ...] = (),
    attacker_within_5_feet: bool | None = None,
) -> RollModifier:
    """Return the attack roll modifier caused by common runtime conditions."""

    advantage: AdvantageState = "normal"
    reasons: list[str] = []

    if _has_any(attacker_conditions, ("blinded", "poisoned", "prone", "restrained")):
        advantage = combine_advantage(advantage, "disadvantage")
        reasons.append("attacker_condition")

    if _has_any(target_conditions, ("blinded", "paralyzed", "restrained", "stunned", "unconscious")):
        advantage = combine_advantage(advantage, "advantage")
        reasons.append("target_condition")

    if "prone" in target_conditions and attacker_within_5_feet is not None:
        if attacker_within_5_feet:
            advantage = combine_advantage(advantage, "advantage")
            reasons.append("target_prone_nearby")
        else:
            advantage = combine_advantage(advantage, "disadvantage")
            reasons.append("target_prone_at_range")

    return RollModifier(advantage=advantage, reasons=tuple(reasons))


def condition_ability_check_modifier(conditions: tuple[ConditionName, ...]) -> RollModifier:
    """Return the ability-check modifier caused by common runtime conditions."""

    if _has_any(conditions, ("poisoned", "frightened")):
        return RollModifier(advantage="disadvantage", reasons=("condition",))
    return RollModifier()


def condition_saving_throw_modifier(
    conditions: tuple[ConditionName, ...],
    ability: Ability,
) -> RollModifier:
    """Return the saving throw modifier caused by common runtime conditions."""

    if ability == "dex" and "restrained" in conditions:
        return RollModifier(advantage="disadvantage", reasons=("restrained",))
    return RollModifier()


def condition_auto_fails_save(conditions: tuple[ConditionName, ...], ability: Ability) -> bool:
    """Return whether conditions cause an automatic Strength or Dexterity save failure."""

    return ability in {"str", "dex"} and _has_any(
        conditions,
        ("paralyzed", "petrified", "stunned", "unconscious"),
    )


def condition_prevents_actions(conditions: tuple[ConditionName, ...]) -> bool:
    """Return whether any condition prevents the combatant from taking actions."""

    return _has_any(conditions, ("incapacitated", "paralyzed", "petrified", "stunned", "unconscious"))


def condition_forces_nearby_critical(conditions: tuple[ConditionName, ...]) -> bool:
    """Return whether hits from nearby attackers become critical hits."""

    return _has_any(conditions, ("paralyzed", "unconscious"))


def adjust_damage_for_target(
    *,
    amount: int,
    damage_type: DamageType,
    target_source: Any | None = None,
) -> DamageAdjustmentResult:
    """Apply source metadata for damage immunity, resistance, and vulnerability."""

    if amount < 0:
        raise ValueError("damage amount cannot be negative")

    immunities = _damage_types(target_source, "damage_immunities")
    resistances = _damage_types(target_source, "damage_resistances")
    vulnerabilities = _damage_types(target_source, "damage_vulnerabilities")
    modifiers: list[str] = []
    adjusted = amount

    if damage_type in immunities:
        adjusted = 0
        modifiers.append("immunity")
    else:
        if damage_type in vulnerabilities:
            adjusted *= 2
            modifiers.append("vulnerability")
        if damage_type in resistances:
            adjusted //= 2
            modifiers.append("resistance")

    return DamageAdjustmentResult(
        original=amount,
        adjusted=adjusted,
        damage_type=damage_type,
        modifiers=tuple(modifiers),
    )


def target_immune_to_condition(target_source: Any | None, condition: ConditionName) -> bool:
    """Return whether source metadata makes the target immune to a condition."""

    return condition in tuple(getattr(target_source, "condition_immunities", ()))


def _damage_types(source: Any | None, attribute: str) -> tuple[DamageType, ...]:
    return tuple(getattr(source, attribute, ()))


def _has_any(conditions: tuple[ConditionName, ...], names: tuple[ConditionName, ...]) -> bool:
    return any(name in conditions for name in names)
