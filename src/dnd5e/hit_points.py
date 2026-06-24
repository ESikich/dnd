from __future__ import annotations

from dataclasses import dataclass
from random import random

from dnd5e.abilities import RandomSource, random_die


@dataclass(frozen=True)
class HitPointState:
    current: int
    maximum: int
    temporary: int = 0


@dataclass(frozen=True)
class HitDicePool:
    hit_die: int
    total: int
    remaining: int


@dataclass(frozen=True)
class DeathSaveState:
    successes: int = 0
    failures: int = 0
    stable: bool = False


@dataclass(frozen=True)
class DamageApplicationResult:
    hit_points: HitPointState
    damage: int
    absorbed_by_temporary: int
    applied_to_current: int


@dataclass(frozen=True)
class HealingResult:
    hit_points: HitPointState
    amount: int
    applied: int


@dataclass(frozen=True)
class RestResult:
    hit_points: HitPointState
    hit_dice: tuple[HitDicePool, ...]
    healing: int = 0
    hit_dice_spent: int = 0


@dataclass(frozen=True)
class DeathSaveRollResult:
    state: DeathSaveState
    roll: int
    successes_added: int
    failures_added: int
    restored_to_one_hp: bool = False


def max_hit_points(
    level: int,
    hit_die: int,
    constitution_modifier: int,
    first_level_max: bool = True,
) -> int:
    _require_positive(level, "level")
    _require_positive(hit_die, "hit_die")

    per_level_modifier = level * constitution_modifier
    if first_level_max:
        return hit_die + ((level - 1) * _average_hit_die(hit_die)) + per_level_modifier

    return level * _average_hit_die(hit_die) + per_level_modifier


def create_hit_dice_pool(level: int, hit_die: int) -> HitDicePool:
    _require_positive(level, "level")
    _require_positive(hit_die, "hit_die")
    return HitDicePool(hit_die=hit_die, total=level, remaining=level)


def apply_damage(state: HitPointState, amount: int) -> DamageApplicationResult:
    _require_non_negative(amount, "amount")
    absorbed = min(state.temporary, amount)
    remaining_damage = amount - absorbed
    applied = min(state.current, remaining_damage)

    return DamageApplicationResult(
        hit_points=HitPointState(
            current=state.current - applied,
            maximum=state.maximum,
            temporary=state.temporary - absorbed,
        ),
        damage=amount,
        absorbed_by_temporary=absorbed,
        applied_to_current=applied,
    )


def apply_healing(state: HitPointState, amount: int) -> HealingResult:
    _require_non_negative(amount, "amount")
    if is_dead(state):
        return HealingResult(hit_points=state, amount=amount, applied=0)

    applied = min(amount, state.maximum - state.current)
    return HealingResult(
        hit_points=HitPointState(
            current=state.current + applied,
            maximum=state.maximum,
            temporary=state.temporary,
        ),
        amount=amount,
        applied=applied,
    )


def apply_temporary_hit_points(state: HitPointState, amount: int) -> HitPointState:
    _require_non_negative(amount, "amount")
    if amount <= state.temporary:
        return state

    return HitPointState(current=state.current, maximum=state.maximum, temporary=amount)


def spend_hit_die(
    pool: HitDicePool,
    hit_points: HitPointState,
    constitution_modifier: int,
    roll: int | None = None,
    rng: RandomSource = random,
) -> RestResult:
    if pool.remaining <= 0:
        raise ValueError("no hit dice remaining")

    die_roll = _roll_hit_die(pool.hit_die, roll, rng)
    healing = max(1, die_roll + constitution_modifier)
    healing_result = apply_healing(hit_points, healing)

    return RestResult(
        hit_points=healing_result.hit_points,
        hit_dice=(
            HitDicePool(
                hit_die=pool.hit_die,
                total=pool.total,
                remaining=pool.remaining - 1,
            ),
        ),
        healing=healing_result.applied,
        hit_dice_spent=1,
    )


def short_rest(
    pool: HitDicePool,
    hit_points: HitPointState,
    constitution_modifier: int,
    rolls: tuple[int, ...] = (),
    rng: RandomSource = random,
) -> RestResult:
    current_pool = pool
    current_hp = hit_points
    total_healing = 0
    spent = 0

    for roll in rolls:
        result = spend_hit_die(current_pool, current_hp, constitution_modifier, roll=roll, rng=rng)
        current_pool = result.hit_dice[0]
        current_hp = result.hit_points
        total_healing += result.healing
        spent += result.hit_dice_spent

    return RestResult(
        hit_points=current_hp,
        hit_dice=(current_pool,),
        healing=total_healing,
        hit_dice_spent=spent,
    )


def long_rest(hit_points: HitPointState, pools: tuple[HitDicePool, ...]) -> RestResult:
    restored_hp = HitPointState(current=hit_points.maximum, maximum=hit_points.maximum, temporary=0)
    recovered_pools = tuple(_recover_hit_dice(pool) for pool in pools)

    return RestResult(hit_points=restored_hp, hit_dice=recovered_pools)


def roll_death_save(
    state: DeathSaveState,
    roll: int | None = None,
    rng: RandomSource = random,
) -> DeathSaveRollResult:
    if state.stable or state.failures >= 3:
        die_roll = _roll_death_save(roll, rng)
        return DeathSaveRollResult(state=state, roll=die_roll, successes_added=0, failures_added=0)

    die_roll = _roll_death_save(roll, rng)

    if die_roll == 20:
        return DeathSaveRollResult(
            state=DeathSaveState(),
            roll=die_roll,
            successes_added=0,
            failures_added=0,
            restored_to_one_hp=True,
        )

    if die_roll == 1:
        failures = min(3, state.failures + 2)
        return DeathSaveRollResult(
            state=DeathSaveState(successes=state.successes, failures=failures),
            roll=die_roll,
            successes_added=0,
            failures_added=2,
        )

    if die_roll >= 10:
        successes = min(3, state.successes + 1)
        return DeathSaveRollResult(
            state=DeathSaveState(
                successes=successes,
                failures=state.failures,
                stable=successes >= 3,
            ),
            roll=die_roll,
            successes_added=1,
            failures_added=0,
        )

    failures = min(3, state.failures + 1)
    return DeathSaveRollResult(
        state=DeathSaveState(successes=state.successes, failures=failures),
        roll=die_roll,
        successes_added=0,
        failures_added=1,
    )


def is_conscious(state: HitPointState) -> bool:
    return state.current > 0


def is_downed(state: HitPointState) -> bool:
    return state.current == 0


def is_dead(state: HitPointState) -> bool:
    return state.maximum <= 0


def _average_hit_die(hit_die: int) -> int:
    return (hit_die // 2) + 1


def _recover_hit_dice(pool: HitDicePool) -> HitDicePool:
    recovered = max(1, pool.total // 2)
    return HitDicePool(
        hit_die=pool.hit_die,
        total=pool.total,
        remaining=min(pool.total, pool.remaining + recovered),
    )


def _roll_hit_die(hit_die: int, roll: int | None, rng: RandomSource) -> int:
    if roll is not None:
        if not 1 <= roll <= hit_die:
            raise ValueError(f"roll must be from 1 to {hit_die}")
        return roll

    return random_die(hit_die, rng)


def _roll_death_save(roll: int | None, rng: RandomSource) -> int:
    if roll is not None:
        if not 1 <= roll <= 20:
            raise ValueError("roll must be from 1 to 20")
        return roll

    return random_die(20, rng)


def _require_positive(value: int, name: str) -> None:
    if value < 1:
        raise ValueError(f"{name} must be positive")


def _require_non_negative(value: int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
