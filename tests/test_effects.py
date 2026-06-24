import pytest

from dnd5e import (
    ArmorClassModifier,
    DamageAdjustmentResult,
    HitPointState,
    RollModifier,
    TurnEffect,
    apply_turn_effects,
    adjust_damage_for_target,
    apply_combat_damage,
    apply_condition,
    combatant_by_id,
    condition_ability_check_modifier,
    condition_attack_modifier,
    create_combat,
    create_combatant,
    create_creature_instance,
    creature_runtime_combatant,
    modified_armor_class,
    resolve_attack_action,
    resolve_spell_save_damage,
    saving_throw,
)


def test_public_effect_imports_and_condition_modifiers() -> None:
    assert RollModifier.__doc__
    assert DamageAdjustmentResult.__doc__
    assert ArmorClassModifier.__doc__
    assert TurnEffect.__doc__
    assert condition_ability_check_modifier(("poisoned",)).advantage == "disadvantage"
    assert condition_attack_modifier(attacker_conditions=("restrained",)).advantage == "disadvantage"
    assert condition_attack_modifier(target_conditions=("restrained",)).advantage == "advantage"


def test_poisoned_attacker_has_disadvantage_on_attack_rolls() -> None:
    combat = apply_condition(simple_effect_combat(), target_id="hero", condition="poisoned")

    result = resolve_attack_action(
        combat,
        actor_id="hero",
        target_id="goblin",
        attack_bonus=10,
        damage_dice="1d8",
        damage_type="slashing",
        attack_rng=fixed_rolls(0.9, 0.1),
    )

    assert result.attack.roll == 3
    assert result.attack.discarded_roll == 19
    assert result.attack.outcome == "miss"
    assert result.damage is None


def test_restrained_target_grants_attack_advantage_and_has_dex_save_disadvantage() -> None:
    combat = apply_condition(simple_effect_combat(), target_id="goblin", condition="restrained")

    attack = resolve_attack_action(
        combat,
        actor_id="hero",
        target_id="goblin",
        attack_bonus=0,
        damage_dice="1d8",
        damage_type="slashing",
        attack_rng=fixed_rolls(0.1, 0.9),
        damage_rng=lambda: 0,
    )
    save = resolve_spell_save_damage(
        combat,
        target_id="goblin",
        save_ability="dex",
        save_bonus=10,
        save_dc=15,
        damage_dice="1d8",
        damage_type="radiant",
        save_rng=fixed_rolls(0.9, 0.1),
        damage_rng=lambda: 0,
    )

    assert attack.attack.roll == 19
    assert attack.attack.discarded_roll == 3
    assert attack.hit
    assert save.save.roll == 3
    assert save.save.discarded_roll == 19
    assert save.save.success is False


def test_prone_target_depends_on_attack_distance() -> None:
    combat = apply_condition(simple_effect_combat(), target_id="goblin", condition="prone")

    nearby = resolve_attack_action(
        combat,
        actor_id="hero",
        target_id="goblin",
        attack_bonus=0,
        damage_dice="1d8",
        damage_type="slashing",
        attacker_within_5_feet=True,
        attack_rng=fixed_rolls(0.1, 0.9),
        damage_rng=lambda: 0,
    )
    ranged = resolve_attack_action(
        combat,
        actor_id="hero",
        target_id="goblin",
        attack_bonus=10,
        damage_dice="1d8",
        damage_type="slashing",
        attacker_within_5_feet=False,
        attack_rng=fixed_rolls(0.9, 0.1),
    )

    assert nearby.attack.roll == 19
    assert nearby.hit
    assert ranged.attack.roll == 3
    assert ranged.attack.outcome == "miss"


def test_unconscious_target_forces_nearby_hits_to_critical_and_auto_fails_dex_saves() -> None:
    combat = apply_condition(simple_effect_combat(), target_id="goblin", condition="unconscious")

    attack = resolve_attack_action(
        combat,
        actor_id="hero",
        target_id="goblin",
        attack_bonus=6,
        damage_dice="1d8",
        damage_type="slashing",
        roll=12,
        attacker_within_5_feet=True,
        damage_rng=lambda: 0,
    )
    save = saving_throw(
        ability="dex",
        save_bonus=20,
        dc=15,
        roll=10,
        conditions=("unconscious",),
    )

    assert attack.attack.outcome == "critical-hit"
    assert attack.damage is not None
    assert attack.damage.rolls[0].notation == "2d8"
    assert save.total == 30
    assert save.success is False


def test_conditions_that_prevent_actions_block_attack_resolution() -> None:
    combat = apply_condition(simple_effect_combat(), target_id="hero", condition="unconscious")

    with pytest.raises(ValueError, match="cannot act"):
        resolve_attack_action(
            combat,
            actor_id="hero",
            target_id="goblin",
            attack_bonus=6,
            damage_dice="1d8",
            damage_type="slashing",
            roll=12,
        )


def test_damage_pipeline_applies_creature_vulnerability_resistance_and_immunity() -> None:
    skeleton = create_creature_instance("skeleton")
    ooze = create_creature_instance("gray_ooze")
    combat = create_combat(
        [
            create_combatant(id="hero", name="Hero", initiative_bonus=2, roll=12),
            creature_runtime_combatant(skeleton, roll=10),
            creature_runtime_combatant(ooze, roll=8),
        ]
    )

    vulnerable = apply_combat_damage(combat, target_id="skeleton", amount=4, damage_type="bludgeoning")
    immune = apply_combat_damage(combat, target_id="skeleton", amount=4, damage_type="poison")
    resisted = apply_combat_damage(combat, target_id="gray_ooze", amount=5, damage_type="fire")

    assert vulnerable.damage_adjustment is not None
    assert vulnerable.damage_adjustment.adjusted == 8
    assert vulnerable.damage_application.applied_to_current == 8
    assert immune.damage_adjustment is not None
    assert immune.damage_adjustment.adjusted == 0
    assert immune.damage_application.applied_to_current == 0
    assert resisted.damage_adjustment is not None
    assert resisted.damage_adjustment.adjusted == 2
    assert resisted.damage_application.applied_to_current == 2


def test_condition_immunity_prevents_condition_application() -> None:
    ghoul = create_creature_instance("ghoul")
    combat = create_combat(
        [
            create_combatant(id="hero", name="Hero", initiative_bonus=2, roll=12),
            creature_runtime_combatant(ghoul, roll=10),
        ]
    )

    next_state = apply_condition(combat, target_id="ghoul", condition="poisoned")

    assert combatant_by_id(next_state, "ghoul").conditions == ()


def test_armor_class_effect_modifiers_change_attack_target_ac() -> None:
    combat = simple_effect_combat()
    shield = ArmorClassModifier(bonus=5, reason="shield")

    armor_class = modified_armor_class(15, (shield,))
    attack = resolve_attack_action(
        combat,
        actor_id="hero",
        target_id="goblin",
        attack_bonus=5,
        damage_dice="1d8",
        damage_type="slashing",
        roll=10,
        target_armor_class_modifiers=(shield,),
    )

    assert armor_class.total == 20
    assert attack.attack.target_armor_class == 20
    assert attack.attack.outcome == "miss"


def test_turn_start_and_end_effect_hooks_apply_state_changes() -> None:
    combat = apply_condition(
        create_combat(
            [
                create_combatant(
                    id="hero",
                    name="Hero",
                    initiative_bonus=2,
                    roll=12,
                    armor_class=16,
                    hit_points=HitPointState(current=20, maximum=20),
                ),
                create_combatant(id="goblin", name="Goblin", initiative_bonus=2, roll=10),
            ]
        ),
        target_id="hero",
        condition="poisoned",
    )
    effects = (
        TurnEffect(name="ongoing fire", timing="start", damage=4, damage_type="fire"),
        TurnEffect(name="regeneration", timing="start", healing=2),
        TurnEffect(name="poison ends", timing="end", remove_conditions=("poisoned",)),
    )

    start = apply_turn_effects(combat, target_id="hero", timing="start", effects=effects)
    end = apply_turn_effects(start.state, target_id="hero", timing="end", effects=effects)

    assert start.applications[0].damage_applied == 4
    assert start.applications[1].healing_applied == 2
    assert combatant_by_id(start.state, "hero").hit_points.current == 18
    assert start.changed
    assert end.applications[0].conditions_removed == ("poisoned",)
    assert combatant_by_id(end.state, "hero").conditions == ()


def test_damage_adjustment_rejects_negative_amounts() -> None:
    with pytest.raises(ValueError, match="damage amount cannot be negative"):
        adjust_damage_for_target(amount=-1, damage_type="fire")


def test_turn_effects_validate_impossible_values() -> None:
    with pytest.raises(ValueError, match="armor class modifier reason is required"):
        ArmorClassModifier(bonus=1, reason="")

    with pytest.raises(ValueError, match="turn effect damage type is required"):
        TurnEffect(name="ongoing fire", timing="start", damage=1)

    with pytest.raises(ValueError, match="unknown turn effect timing"):
        apply_turn_effects(simple_effect_combat(), target_id="hero", timing="middle", effects=())


def simple_effect_combat():
    return create_combat(
        [
            create_combatant(id="hero", name="Hero", initiative_bonus=2, roll=12, armor_class=16),
            create_combatant(id="goblin", name="Goblin", initiative_bonus=2, roll=10, armor_class=15),
        ]
    )


def fixed_rolls(*values: float):
    iterator = iter(values)

    def rng() -> float:
        return next(iterator)

    return rng
