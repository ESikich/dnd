from __future__ import annotations

import re
from dataclasses import dataclass
from random import random

from dnd5e.abilities import RandomSource
from dnd5e.combat import CombatState
from dnd5e.equipment import MAGIC_ITEMS, WEAPONS, MagicItemDefinition, MagicItemEffect
from dnd5e.spells import SpellConditionResult, apply_spell_condition


@dataclass(frozen=True)
class MagicItemChargeState:
    """Runtime charge state for a magic item with limited-use effects."""

    item: MagicItemDefinition
    maximum: int
    remaining: int

    def __post_init__(self) -> None:
        if self.maximum < 1:
            raise ValueError("magic item maximum charges must be positive")
        if not 0 <= self.remaining <= self.maximum:
            raise ValueError("magic item remaining charges must be from 0 to maximum")


@dataclass(frozen=True)
class MagicItemRechargeResult:
    """Result of restoring charges to a magic item."""

    state: MagicItemChargeState
    restored: int
    roll_total: int | None = None

    def __post_init__(self) -> None:
        if self.restored < 0:
            raise ValueError("restored charges cannot be negative")
        if self.roll_total is not None and self.roll_total < 1:
            raise ValueError("magic item recharge roll total must be positive")


def active_magic_items(
    magic_items: tuple[str | MagicItemDefinition, ...],
    attuned_magic_items: tuple[str | MagicItemDefinition, ...] = (),
) -> tuple[MagicItemDefinition, ...]:
    """Return items whose passive effects are active for an equipped loadout."""

    attuned_ids = {_resolve_magic_item(item).id for item in attuned_magic_items}
    return tuple(
        item
        for item in (_resolve_magic_item(magic_item) for magic_item in magic_items)
        if not item.requires_attunement or item.id in attuned_ids
    )


def magic_item_armor_class_bonus(items: tuple[str | MagicItemDefinition, ...]) -> int:
    """Return total flat AC bonus from active magic item effects."""

    return _sum_effect_bonuses(items, "armor_class_bonus")


def magic_item_saving_throw_bonus(items: tuple[str | MagicItemDefinition, ...]) -> int:
    """Return total flat saving throw bonus from active magic item effects."""

    return _sum_effect_bonuses(items, "saving_throw_bonus")


def magic_item_spell_attack_bonus(items: tuple[str | MagicItemDefinition, ...]) -> int:
    """Return total flat spell attack bonus from active magic item effects."""

    return _sum_effect_bonuses(items, "spell_attack_bonus")


def magic_item_weapon_bonus(
    items: tuple[str | MagicItemDefinition, ...],
    weapon: str,
) -> int:
    """Return attack and damage bonus from active magic item effects for one weapon."""

    return sum(
        effect.bonus or 0
        for item in (_resolve_magic_item(magic_item) for magic_item in items)
        for effect in item.effects
        if effect.kind == "attack_damage_bonus" and _magic_item_applies_to_weapon(item, weapon)
    )


def magic_item_extra_damage(
    items: tuple[str | MagicItemDefinition, ...],
    weapon: str,
) -> tuple[MagicItemEffect, ...]:
    """Return extra damage effects from active magic item effects for one weapon."""

    return tuple(
        effect
        for item in (_resolve_magic_item(magic_item) for magic_item in items)
        for effect in item.effects
        if effect.kind == "extra_damage" and _magic_item_applies_to_weapon(item, weapon)
    )


def create_magic_item_charge_state(item: str | MagicItemDefinition) -> MagicItemChargeState:
    """Create a full charge state from the first charged effect on a magic item."""

    definition = _resolve_magic_item(item)
    maximum = _magic_item_maximum_charges(definition)
    if maximum is None:
        raise ValueError(f"magic item has no charges: {definition.id}")
    return MagicItemChargeState(item=definition, maximum=maximum, remaining=maximum)


def spend_magic_item_charges(state: MagicItemChargeState, charges: int = 1) -> MagicItemChargeState:
    """Spend charges from a magic item and return updated state."""

    if charges < 1:
        raise ValueError("spent magic item charges must be positive")
    if state.remaining < charges:
        raise ValueError(f"not enough charges remaining for magic item: {state.item.id}")
    return MagicItemChargeState(
        item=state.item,
        maximum=state.maximum,
        remaining=state.remaining - charges,
    )


def recharge_magic_item(
    state: MagicItemChargeState,
    *,
    rng: RandomSource = random,
) -> MagicItemRechargeResult:
    """Recharge a magic item from its SRD-style recharge expression."""

    recharge = _magic_item_recharge(state.item)
    if recharge is None:
        restored = state.maximum - state.remaining
        return MagicItemRechargeResult(
            state=MagicItemChargeState(state.item, state.maximum, state.maximum),
            restored=restored,
        )

    roll_total = _roll_recharge(recharge, rng)
    next_remaining = min(state.maximum, state.remaining + roll_total)
    return MagicItemRechargeResult(
        state=MagicItemChargeState(state.item, state.maximum, next_remaining),
        restored=next_remaining - state.remaining,
        roll_total=roll_total,
    )


def apply_magic_item_condition(
    state: CombatState,
    item: str | MagicItemDefinition,
    *,
    target_id: str,
    save_bonus: int,
    roll: int | None = None,
    save_rng: RandomSource = random,
) -> SpellConditionResult:
    """Apply a condition-save magic item effect to one combat target."""

    effect = _condition_save_effect(_resolve_magic_item(item))
    if effect.save_ability is None or effect.save_dc is None or effect.condition is None:
        raise ValueError("magic item condition effect is incomplete")
    return apply_spell_condition(
        state,
        target_id=target_id,
        condition=effect.condition,  # type: ignore[arg-type]
        save_ability=effect.save_ability,  # type: ignore[arg-type]
        save_bonus=save_bonus,
        save_dc=effect.save_dc,
        roll=roll,
        save_rng=save_rng,
    )


def _sum_effect_bonuses(items: tuple[str | MagicItemDefinition, ...], kind: str) -> int:
    return sum(
        effect.bonus or 0
        for item in (_resolve_magic_item(magic_item) for magic_item in items)
        for effect in item.effects
        if effect.kind == kind
    )


def _magic_item_applies_to_weapon(item: MagicItemDefinition, weapon: str) -> bool:
    weapon_definition = WEAPONS[weapon]
    if item.base_item_id == weapon:
        return True
    if item.base_item_id == "staff" and weapon == "quarterstaff":
        return True
    if "any" in item.applicable_items:
        return item.category == "Weapon"
    if "any_sword" in item.applicable_items:
        return weapon in {"greatsword", "longsword", "rapier", "scimitar", "shortsword"}
    return weapon in item.applicable_items or weapon_definition.category in item.applicable_items


def _magic_item_maximum_charges(item: MagicItemDefinition) -> int | None:
    charges = [effect.charges for effect in item.effects if effect.charges is not None]
    if not charges:
        return None
    return max(charges)


def _magic_item_recharge(item: MagicItemDefinition) -> str | None:
    for effect in item.effects:
        if effect.recharge is not None:
            return effect.recharge
    return None


def _condition_save_effect(item: MagicItemDefinition) -> MagicItemEffect:
    for effect in item.effects:
        if effect.kind == "condition_save":
            return effect
    raise ValueError(f"magic item has no condition-save effect: {item.id}")


def _roll_recharge(recharge: str, rng: RandomSource) -> int:
    dice_match = re.search(r"(\d+)d(\d+)(?:\s*\+\s*(\d+))?", recharge)
    if dice_match is None:
        flat_match = re.search(r"(\d+)", recharge)
        if flat_match is None:
            raise ValueError(f"unsupported magic item recharge expression: {recharge}")
        return int(flat_match.group(1))

    count = int(dice_match.group(1))
    sides = int(dice_match.group(2))
    modifier = int(dice_match.group(3) or 0)
    return sum(int(rng() * sides) + 1 for _ in range(count)) + modifier


def _resolve_magic_item(item: str | MagicItemDefinition) -> MagicItemDefinition:
    if isinstance(item, MagicItemDefinition):
        return item
    return MAGIC_ITEMS[item]
