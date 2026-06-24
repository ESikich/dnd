from __future__ import annotations

import re
from dataclasses import dataclass, field
from random import random
from typing import Any

from dnd5e.abilities import RandomSource, d20_check
from dnd5e.character import CharacterRules, initiative_bonus
from dnd5e.dice import DiceRoll, roll_dice
from dnd5e.hit_points import (
    DamageApplicationResult,
    HealingResult,
    HitPointState,
    apply_damage,
    apply_healing,
    is_downed,
)
from dnd5e.types import AdvantageState, AttackOutcome, ConditionName, DamageType


@dataclass(frozen=True)
class Combatant:
    id: str
    name: str
    initiative_bonus: int
    initiative: int
    armor_class: int = 10
    hit_points: HitPointState = field(default_factory=lambda: HitPointState(current=1, maximum=1))
    conditions: tuple[ConditionName, ...] = ()
    source: Any | None = None


@dataclass(frozen=True)
class CombatState:
    round: int
    turn_index: int
    order: tuple[Combatant, ...]

    @property
    def current(self) -> Combatant:
        return self.order[self.turn_index]


@dataclass(frozen=True)
class AttackRollResult:
    roll: int
    total: int
    target_armor_class: int
    outcome: AttackOutcome
    discarded_roll: int | None = None


@dataclass(frozen=True)
class DamageResult:
    type: DamageType
    rolls: tuple[DiceRoll, ...]
    total: int


@dataclass(frozen=True)
class AttackActionResult:
    state: CombatState
    actor: Combatant
    target_before: Combatant
    target_after: Combatant
    attack: AttackRollResult
    damage: DamageResult | None = None
    damage_application: DamageApplicationResult | None = None

    @property
    def hit(self) -> bool:
        return self.attack.outcome in {"hit", "critical-hit"}

    @property
    def target_defeated(self) -> bool:
        return combatant_defeated(self.target_after)


@dataclass(frozen=True)
class CombatHealingResult:
    state: CombatState
    target_before: Combatant
    target_after: Combatant
    healing: HealingResult


def create_combatant(
    *,
    id: str,
    name: str,
    initiative_bonus: int,
    roll: int = 0,
    armor_class: int = 10,
    hit_points: HitPointState | None = None,
    conditions: tuple[ConditionName, ...] = (),
    source: Any | None = None,
) -> Combatant:
    return Combatant(
        id=id,
        name=name,
        initiative_bonus=initiative_bonus,
        initiative=roll + initiative_bonus,
        armor_class=armor_class,
        hit_points=hit_points or HitPointState(current=1, maximum=1),
        conditions=tuple(dict.fromkeys(conditions)),
        source=source,
    )


def character_runtime_combatant(
    character: CharacterRules,
    *,
    id: str,
    name: str,
    roll: int = 0,
    armor_class: int,
    hit_points: HitPointState,
    conditions: tuple[ConditionName, ...] = (),
) -> Combatant:
    return create_combatant(
        id=id,
        name=name,
        initiative_bonus=initiative_bonus(character),
        roll=roll,
        armor_class=armor_class,
        hit_points=hit_points,
        conditions=conditions,
        source=character,
    )


def create_combat(combatants: list[Combatant | dict[str, object]]) -> CombatState:
    if not combatants:
        raise ValueError("combat requires at least one combatant")

    runtime_combatants = tuple(
        combatant if isinstance(combatant, Combatant) else _combatant_from_mapping(combatant)
        for combatant in combatants
    )
    if len({combatant.id for combatant in runtime_combatants}) != len(runtime_combatants):
        raise ValueError("combatant ids must be unique")

    order = tuple(
        sorted(
            runtime_combatants,
            key=lambda combatant: (
                -combatant.initiative,
                -combatant.initiative_bonus,
                combatant.name,
            ),
        )
    )

    return CombatState(round=1, turn_index=0, order=order)


def combatant_by_id(state: CombatState, id: str) -> Combatant:
    for combatant in state.order:
        if combatant.id == id:
            return combatant
    raise KeyError(id)


def next_turn(state: CombatState) -> CombatState:
    next_index = (state.turn_index + 1) % len(state.order)
    next_round = state.round + 1 if next_index == 0 else state.round

    return CombatState(round=next_round, turn_index=next_index, order=state.order)


def attack_roll(
    *,
    attacker_bonus: int,
    target_armor_class: int,
    roll: int | None = None,
    advantage: AdvantageState = "normal",
    rng: RandomSource = random,
    critical_hit_at: int = 20,
) -> AttackRollResult:
    check = d20_check(
        ability_score=10,
        bonus=attacker_bonus,
        roll=roll,
        advantage=advantage,
        rng=rng,
    )
    total = check.roll + attacker_bonus

    return AttackRollResult(
        roll=check.roll,
        discarded_roll=check.discarded_roll,
        total=total,
        target_armor_class=target_armor_class,
        outcome=_resolve_attack_outcome(check.roll, total, target_armor_class, critical_hit_at),
    )


def damage_roll(
    *,
    dice: str,
    type: DamageType,
    critical: bool = False,
    bonus_dice: tuple[str, ...] = (),
    rng: RandomSource = random,
) -> DamageResult:
    rolls = (
        roll_dice(_double_dice(dice) if critical else dice, rng=rng),
        *(
            roll_dice(_double_dice(extra_dice) if critical else extra_dice, rng=rng)
            for extra_dice in bonus_dice
        ),
    )

    return DamageResult(type=type, rolls=rolls, total=sum(roll.total for roll in rolls))


def resolve_attack_action(
    state: CombatState,
    *,
    actor_id: str,
    target_id: str,
    attack_bonus: int,
    damage_dice: str,
    damage_type: DamageType,
    roll: int | None = None,
    advantage: AdvantageState = "normal",
    damage_rng: RandomSource = random,
    attack_rng: RandomSource = random,
    bonus_dice: tuple[str, ...] = (),
) -> AttackActionResult:
    actor = combatant_by_id(state, actor_id)
    target = combatant_by_id(state, target_id)
    attack = attack_roll(
        attacker_bonus=attack_bonus,
        target_armor_class=target.armor_class,
        roll=roll,
        advantage=advantage,
        rng=attack_rng,
    )

    damage = None
    damage_application = None
    target_after = target
    next_state = state

    if attack.outcome in {"hit", "critical-hit"}:
        damage = damage_roll(
            dice=damage_dice,
            type=damage_type,
            critical=attack.outcome == "critical-hit",
            bonus_dice=bonus_dice,
            rng=damage_rng,
        )
        damage_application = apply_damage(target.hit_points, damage.total)
        target_after = _replace_combatant(target, hit_points=damage_application.hit_points)
        next_state = _replace_in_state(state, target_after)

    return AttackActionResult(
        state=next_state,
        actor=actor,
        target_before=target,
        target_after=target_after,
        attack=attack,
        damage=damage,
        damage_application=damage_application,
    )


def apply_combat_healing(
    state: CombatState,
    *,
    target_id: str,
    amount: int,
) -> CombatHealingResult:
    target = combatant_by_id(state, target_id)
    healing = apply_healing(target.hit_points, amount)
    target_after = _replace_combatant(target, hit_points=healing.hit_points)

    return CombatHealingResult(
        state=_replace_in_state(state, target_after),
        target_before=target,
        target_after=target_after,
        healing=healing,
    )


def apply_condition(
    state: CombatState,
    *,
    target_id: str,
    condition: ConditionName,
) -> CombatState:
    target = combatant_by_id(state, target_id)
    if condition in target.conditions:
        return state

    return _replace_in_state(
        state,
        _replace_combatant(target, conditions=(*target.conditions, condition)),
    )


def remove_condition(
    state: CombatState,
    *,
    target_id: str,
    condition: ConditionName,
) -> CombatState:
    target = combatant_by_id(state, target_id)
    if condition not in target.conditions:
        return state

    return _replace_in_state(
        state,
        _replace_combatant(
            target,
            conditions=tuple(existing for existing in target.conditions if existing != condition),
        ),
    )


def combatant_defeated(combatant: Combatant) -> bool:
    return is_downed(combatant.hit_points)


def _resolve_attack_outcome(
    natural: int,
    total: int,
    armor_class: int,
    critical_hit_at: int,
) -> AttackOutcome:
    if natural == 1:
        return "critical-miss"
    if natural >= critical_hit_at:
        return "critical-hit"
    return "hit" if total >= armor_class else "miss"


def _double_dice(notation: str) -> str:
    match = re.match(r"^(\d*)d(\d+)([+-]\d+)?$", notation.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(f"invalid dice notation: {notation}")

    count = int(match.group(1) or "1")
    return f"{count * 2}d{match.group(2)}{match.group(3) or ''}"


def _combatant_from_mapping(combatant: dict[str, object]) -> Combatant:
    hit_points = combatant.get("hit_points")
    if hit_points is None:
        hp = HitPointState(current=1, maximum=1)
    elif isinstance(hit_points, HitPointState):
        hp = hit_points
    else:
        hp = HitPointState(current=int(hit_points), maximum=int(hit_points))

    return create_combatant(
        id=str(combatant["id"]),
        name=str(combatant["name"]),
        initiative_bonus=int(combatant["initiative_bonus"]),
        roll=int(combatant.get("roll", 0)),
        armor_class=int(combatant.get("armor_class", combatant.get("ac", 10))),
        hit_points=hp,
        conditions=tuple(combatant.get("conditions", ())),  # type: ignore[arg-type]
        source=combatant.get("source"),
    )


def _replace_combatant(
    combatant: Combatant,
    *,
    hit_points: HitPointState | None = None,
    conditions: tuple[ConditionName, ...] | None = None,
) -> Combatant:
    return Combatant(
        id=combatant.id,
        name=combatant.name,
        initiative_bonus=combatant.initiative_bonus,
        initiative=combatant.initiative,
        armor_class=combatant.armor_class,
        hit_points=hit_points or combatant.hit_points,
        conditions=combatant.conditions if conditions is None else conditions,
        source=combatant.source,
    )


def _replace_in_state(state: CombatState, combatant: Combatant) -> CombatState:
    order = tuple(
        combatant if existing.id == combatant.id else existing
        for existing in state.order
    )
    return CombatState(round=state.round, turn_index=state.turn_index, order=order)
