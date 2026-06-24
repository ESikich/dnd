from dnd5e import (
    DamageApplicationResult,
    DeathSaveRollResult,
    DeathSaveState,
    HealingResult,
    HitDicePool,
    HitPointState,
    RestResult,
    apply_damage,
    apply_healing,
    apply_temporary_hit_points,
    create_hit_dice_pool,
    is_conscious,
    is_dead,
    is_downed,
    long_rest,
    max_hit_points,
    roll_death_save,
    short_rest,
    spend_hit_die,
)


def test_public_hit_point_imports() -> None:
    assert HitPointState(current=1, maximum=1).current == 1
    assert HitDicePool(hit_die=10, total=1, remaining=1).hit_die == 10
    assert DeathSaveState().successes == 0
    assert DamageApplicationResult is not None
    assert HealingResult is not None
    assert RestResult is not None
    assert DeathSaveRollResult is not None


def test_max_hit_points_uses_max_first_level_and_average_later_levels() -> None:
    assert max_hit_points(level=1, hit_die=10, constitution_modifier=2) == 12
    assert max_hit_points(level=5, hit_die=10, constitution_modifier=2) == 44
    assert max_hit_points(level=5, hit_die=10, constitution_modifier=2, first_level_max=False) == 40


def test_damage_without_temporary_hp_reduces_current_hp() -> None:
    state = HitPointState(current=12, maximum=20)

    result = apply_damage(state, 5)

    assert result.hit_points == HitPointState(current=7, maximum=20)
    assert result.absorbed_by_temporary == 0
    assert result.applied_to_current == 5


def test_damage_consumes_temporary_hp_first() -> None:
    state = HitPointState(current=12, maximum=20, temporary=3)

    result = apply_damage(state, 5)

    assert result.hit_points == HitPointState(current=10, maximum=20, temporary=0)
    assert result.absorbed_by_temporary == 3
    assert result.applied_to_current == 2


def test_damage_does_not_reduce_current_below_zero() -> None:
    state = HitPointState(current=4, maximum=20)

    result = apply_damage(state, 99)

    assert result.hit_points.current == 0
    assert result.applied_to_current == 4


def test_healing_caps_at_maximum_hp() -> None:
    state = HitPointState(current=17, maximum=20)

    result = apply_healing(state, 10)

    assert result.hit_points == HitPointState(current=20, maximum=20)
    assert result.applied == 3


def test_temporary_hp_only_replaces_when_higher() -> None:
    state = HitPointState(current=10, maximum=20, temporary=5)

    assert apply_temporary_hit_points(state, 3) == state
    assert apply_temporary_hit_points(state, 8) == HitPointState(current=10, maximum=20, temporary=8)


def test_conscious_downed_and_dead_predicates() -> None:
    assert is_conscious(HitPointState(current=1, maximum=10))
    assert is_downed(HitPointState(current=0, maximum=10))
    assert is_dead(HitPointState(current=0, maximum=0))


def test_spending_hit_die_decreases_pool_and_heals_minimum_one() -> None:
    pool = create_hit_dice_pool(level=3, hit_die=8)
    hp = HitPointState(current=5, maximum=20)

    result = spend_hit_die(pool, hp, constitution_modifier=2, roll=4)

    assert result.hit_points == HitPointState(current=11, maximum=20)
    assert result.hit_dice == (HitDicePool(hit_die=8, total=3, remaining=2),)
    assert result.healing == 6
    assert result.hit_dice_spent == 1

    minimum = spend_hit_die(pool, hp, constitution_modifier=-5, roll=1)
    assert minimum.healing == 1


def test_short_rest_spends_multiple_hit_dice() -> None:
    pool = create_hit_dice_pool(level=3, hit_die=8)
    hp = HitPointState(current=5, maximum=20)

    result = short_rest(pool, hp, constitution_modifier=1, rolls=(4, 5))

    assert result.hit_points == HitPointState(current=16, maximum=20)
    assert result.hit_dice == (HitDicePool(hit_die=8, total=3, remaining=1),)
    assert result.healing == 11
    assert result.hit_dice_spent == 2


def test_long_rest_restores_hp_clears_temporary_hp_and_recovers_hit_dice() -> None:
    hp = HitPointState(current=2, maximum=20, temporary=4)
    pools = (HitDicePool(hit_die=10, total=5, remaining=1),)

    result = long_rest(hp, pools)

    assert result.hit_points == HitPointState(current=20, maximum=20, temporary=0)
    assert result.hit_dice == (HitDicePool(hit_die=10, total=5, remaining=3),)


def test_death_save_normal_success_and_failure() -> None:
    success = roll_death_save(DeathSaveState(), roll=10)
    failure = roll_death_save(DeathSaveState(), roll=9)

    assert success.state == DeathSaveState(successes=1, failures=0)
    assert success.successes_added == 1
    assert failure.state == DeathSaveState(successes=0, failures=1)
    assert failure.failures_added == 1


def test_death_save_natural_one_counts_two_failures() -> None:
    result = roll_death_save(DeathSaveState(failures=1), roll=1)

    assert result.state == DeathSaveState(successes=0, failures=3)
    assert result.failures_added == 2


def test_death_save_natural_twenty_restores_to_one_hp_signal() -> None:
    result = roll_death_save(DeathSaveState(successes=2, failures=2), roll=20)

    assert result.state == DeathSaveState()
    assert result.restored_to_one_hp


def test_death_save_three_successes_stabilizes() -> None:
    result = roll_death_save(DeathSaveState(successes=2), roll=11)

    assert result.state == DeathSaveState(successes=3, failures=0, stable=True)


def test_death_save_three_failures_is_dead_state() -> None:
    result = roll_death_save(DeathSaveState(failures=2), roll=4)

    assert result.state == DeathSaveState(successes=0, failures=3)
