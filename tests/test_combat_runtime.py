import pytest

from dnd5e import (
    AttackActionResult,
    AttackRollResult,
    CharacterRules,
    CombatHealingResult,
    CombatState,
    Combatant,
    DamageResult,
    DiceRoll,
    HitPointState,
    apply_combat_healing,
    apply_condition,
    character_runtime_combatant,
    combatant_by_id,
    combatant_defeated,
    create_combat,
    create_combatant,
    create_creature_instance,
    creature_runtime_combatant,
    next_turn,
    remove_condition,
    resolve_attack_action,
)


def test_public_combat_runtime_imports() -> None:
    assert AttackActionResult is not None
    assert CombatHealingResult is not None


def test_create_combat_accepts_runtime_combatants_with_hp_and_ac() -> None:
    hero = create_combatant(
        id="hero",
        name="Hero",
        initiative_bonus=2,
        roll=12,
        armor_class=18,
        hit_points=HitPointState(current=20, maximum=20),
    )
    goblin = create_creature_instance("goblin", id="goblin-1")

    combat = create_combat([hero, creature_runtime_combatant(goblin, roll=15)])

    assert combat.current.id == "goblin-1"
    assert combatant_by_id(combat, "hero").armor_class == 18
    assert combatant_by_id(combat, "goblin-1").hit_points.current == 7


def test_character_runtime_combatant_uses_character_initiative_bonus() -> None:
    character = CharacterRules(
        level=1,
        abilities={
            "str": 10,
            "dex": 16,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
        },
        initiative_bonus_value=1,
    )

    combatant = character_runtime_combatant(
        character,
        id="hero",
        name="Hero",
        roll=12,
        armor_class=16,
        hit_points=HitPointState(current=12, maximum=12),
    )

    assert combatant.initiative_bonus == 4
    assert combatant.initiative == 16
    assert combatant.source is character


def test_attack_action_miss_does_not_apply_damage() -> None:
    combat = simple_combat()

    result = resolve_attack_action(
        combat,
        actor_id="hero",
        target_id="goblin",
        attack_bonus=4,
        damage_dice="1d8+2",
        damage_type="slashing",
        roll=2,
        damage_rng=lambda: 0,
    )

    assert not result.hit
    assert result.damage is None
    assert combatant_by_id(result.state, "goblin").hit_points.current == 7


def test_attack_action_hit_rolls_damage_and_updates_target_hp() -> None:
    combat = simple_combat()

    result = resolve_attack_action(
        combat,
        actor_id="hero",
        target_id="goblin",
        attack_bonus=6,
        damage_dice="1d8+3",
        damage_type="slashing",
        roll=12,
        damage_rng=lambda: 0,
    )

    assert result.hit
    assert result.damage is not None
    assert result.damage.total == 4
    assert result.damage_application is not None
    assert result.damage_application.applied_to_current == 4
    assert combatant_by_id(result.state, "goblin").hit_points.current == 3


def test_attack_action_critical_hit_doubles_damage_dice_and_can_defeat() -> None:
    combat = create_combat(
        [
            create_combatant(
                id="hero",
                name="Hero",
                initiative_bonus=2,
                roll=10,
                armor_class=16,
                hit_points=HitPointState(current=20, maximum=20),
            ),
            create_combatant(
                id="goblin",
                name="Goblin",
                initiative_bonus=2,
                roll=8,
                armor_class=15,
                hit_points=HitPointState(current=4, maximum=7),
            ),
        ]
    )

    result = resolve_attack_action(
        combat,
        actor_id="hero",
        target_id="goblin",
        attack_bonus=6,
        damage_dice="1d6+2",
        damage_type="slashing",
        roll=20,
        damage_rng=lambda: 0,
    )

    assert result.damage is not None
    assert result.damage.rolls[0].notation == "2d6+2"
    assert result.target_defeated
    assert combatant_defeated(result.target_after)
    assert combatant_by_id(result.state, "goblin").hit_points.current == 0


def test_combat_healing_updates_target_hp() -> None:
    combat = simple_combat()
    damaged = resolve_attack_action(
        combat,
        actor_id="hero",
        target_id="goblin",
        attack_bonus=6,
        damage_dice="1d8+3",
        damage_type="slashing",
        roll=12,
        damage_rng=lambda: 0,
    )

    result = apply_combat_healing(damaged.state, target_id="goblin", amount=2)

    assert result.healing.applied == 2
    assert combatant_by_id(result.state, "goblin").hit_points.current == 5


def test_condition_helpers_add_idempotently_and_remove() -> None:
    combat = simple_combat()

    poisoned = apply_condition(combat, target_id="goblin", condition="poisoned")
    still_poisoned = apply_condition(poisoned, target_id="goblin", condition="poisoned")
    recovered = remove_condition(still_poisoned, target_id="goblin", condition="poisoned")

    assert combatant_by_id(poisoned, "goblin").conditions == ("poisoned",)
    assert combatant_by_id(still_poisoned, "goblin").conditions == ("poisoned",)
    assert combatant_by_id(recovered, "goblin").conditions == ()


def test_turn_advancement_preserves_runtime_state() -> None:
    combat = simple_combat()

    next_state = next_turn(combat)

    assert next_state.current.id == "goblin"
    assert combatant_by_id(next_state, "hero").hit_points.maximum == 20


def test_combatant_validates_impossible_runtime_state() -> None:
    with pytest.raises(ValueError, match="combatant id is required"):
        create_combatant(id="", name="Hero", initiative_bonus=2)

    with pytest.raises(ValueError, match="combatant name is required"):
        create_combatant(id="hero", name="", initiative_bonus=2)

    with pytest.raises(ValueError, match="combatant armor class must be positive"):
        create_combatant(id="hero", name="Hero", initiative_bonus=2, armor_class=0)

    with pytest.raises(ValueError, match="unknown condition: burning"):
        create_combatant(id="hero", name="Hero", initiative_bonus=2, conditions=("burning",))


def test_combat_state_validates_order_and_turn_index() -> None:
    hero = create_combatant(id="hero", name="Hero", initiative_bonus=2)

    with pytest.raises(ValueError, match="combat round must be positive"):
        CombatState(round=0, turn_index=0, order=(hero,))

    with pytest.raises(ValueError, match="combat order cannot be empty"):
        CombatState(round=1, turn_index=0, order=())

    with pytest.raises(ValueError, match="combat turn index must reference the order"):
        CombatState(round=1, turn_index=1, order=(hero,))

    with pytest.raises(ValueError, match="combatant ids must be unique"):
        CombatState(round=1, turn_index=0, order=(hero, hero))


def test_attack_roll_result_validates_impossible_values() -> None:
    with pytest.raises(ValueError, match="attack roll must be from 1 to 20"):
        AttackRollResult(roll=0, total=5, target_armor_class=10, outcome="miss")

    with pytest.raises(ValueError, match="discarded attack roll must be from 1 to 20"):
        AttackRollResult(roll=10, total=15, target_armor_class=10, outcome="hit", discarded_roll=21)

    with pytest.raises(ValueError, match="target armor class must be positive"):
        AttackRollResult(roll=10, total=15, target_armor_class=0, outcome="hit")

    with pytest.raises(ValueError, match="unknown attack outcome: graze"):
        AttackRollResult(roll=10, total=15, target_armor_class=10, outcome="graze")


def test_damage_result_validates_impossible_values() -> None:
    roll = DiceRoll(notation="1d4", rolls=(1,), modifier=0, total=1)

    with pytest.raises(ValueError, match="unknown damage type: holy"):
        DamageResult(type="holy", rolls=(roll,), total=1)

    with pytest.raises(ValueError, match="damage result requires at least one roll"):
        DamageResult(type="radiant", rolls=(), total=1)

    with pytest.raises(ValueError, match="damage total cannot be negative"):
        DamageResult(type="radiant", rolls=(roll,), total=-1)


def simple_combat():
    return create_combat(
        [
            create_combatant(
                id="hero",
                name="Hero",
                initiative_bonus=2,
                roll=14,
                armor_class=18,
                hit_points=HitPointState(current=20, maximum=20),
            ),
            create_combatant(
                id="goblin",
                name="Goblin",
                initiative_bonus=2,
                roll=12,
                armor_class=15,
                hit_points=HitPointState(current=7, maximum=7),
            ),
        ]
    )
