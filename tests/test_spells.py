from typing import cast

import pytest

from dnd5e import (
    SPELLS,
    SPELL_COMPONENTS,
    SPELL_SCHOOLS,
    PactMagicState,
    CharacterRules,
    HitPointState,
    SavingThrowResult,
    SpellConditionResult,
    SpellComponent,
    SpellDefinition,
    SpellHealingResult,
    SpellSaveDamageResult,
    SpellSchool,
    SpellSlotPool,
    SpellSlotState,
    apply_spell_condition,
    apply_spell_healing,
    combatant_by_id,
    create_combat,
    create_combatant,
    create_pact_magic,
    create_spell_slots,
    resolve_spell_attack,
    resolve_spell_save_damage,
    restore_pact_magic,
    restore_spell_slots,
    saving_throw,
    spell_attack_bonus,
    spell_save_dc,
    spell_slots_remaining,
    spend_pact_slot,
    spend_spell_slot,
)


def test_public_spell_imports_and_docstrings() -> None:
    assert "evocation" in SPELL_SCHOOLS
    assert "verbal" in SPELL_COMPONENTS
    assert SpellDefinition.__doc__
    assert SpellSlotPool.__doc__
    assert SpellSlotState.__doc__
    assert PactMagicState.__doc__
    assert SavingThrowResult.__doc__
    assert SpellSaveDamageResult.__doc__
    assert SpellHealingResult.__doc__
    assert SpellConditionResult.__doc__
    assert isinstance(SPELLS["fire_bolt"], SpellDefinition)


def test_spell_catalog_includes_basic_srd_style_metadata() -> None:
    fire_bolt = SPELLS["fire_bolt"]
    detect_magic = SPELLS["detect_magic"]
    mage_armor = SPELLS["mage_armor"]

    assert fire_bolt.level == 0
    assert fire_bolt.school == "evocation"
    assert fire_bolt.range == "120 feet"
    assert fire_bolt.components == ("verbal", "somatic")
    assert detect_magic.concentration is True
    assert detect_magic.ritual is True
    assert mage_armor.material == "cured leather"


def test_spell_definition_rejects_invalid_core_metadata() -> None:
    with pytest.raises(ValueError, match="spell id is required"):
        SpellDefinition("", "Test", 1, "evocation", "1 action", "self", "instantaneous", ("verbal",))

    with pytest.raises(ValueError, match="spell level"):
        SpellDefinition("test", "Test", 10, "evocation", "1 action", "self", "instantaneous", ("verbal",))

    with pytest.raises(ValueError, match="unknown spell school"):
        SpellDefinition(
            "test",
            "Test",
            1,
            cast(SpellSchool, "dunamancy"),
            "1 action",
            "self",
            "instantaneous",
            ("verbal",),
        )

    with pytest.raises(ValueError, match="casting_time is required"):
        SpellDefinition("test", "Test", 1, "evocation", "", "self", "instantaneous", ("verbal",))


def test_spell_definition_rejects_invalid_components() -> None:
    with pytest.raises(ValueError, match="components are required"):
        SpellDefinition("test", "Test", 1, "evocation", "1 action", "self", "instantaneous", ())

    with pytest.raises(ValueError, match="unknown spell component"):
        SpellDefinition(
            "test",
            "Test",
            1,
            "evocation",
            "1 action",
            "self",
            "instantaneous",
            cast(tuple[SpellComponent, ...], ("focus",)),
        )

    with pytest.raises(ValueError, match="requires a material component"):
        SpellDefinition(
            "test",
            "Test",
            1,
            "evocation",
            "1 action",
            "self",
            "instantaneous",
            ("verbal",),
            material="a tiny bell",
        )


def test_spellcasting_helpers_use_ability_and_proficiency() -> None:
    caster = CharacterRules(
        level=5,
        abilities={
            "str": 8,
            "dex": 14,
            "con": 12,
            "int": 16,
            "wis": 10,
            "cha": 13,
        },
    )

    assert spell_attack_bonus(caster, "int") == 6
    assert spell_save_dc(caster, "int") == 14


def test_spellcasting_helpers_accept_flat_bonuses() -> None:
    caster = CharacterRules(
        level=1,
        abilities={
            "str": 8,
            "dex": 10,
            "con": 12,
            "int": 14,
            "wis": 16,
            "cha": 10,
        },
    )

    assert spell_attack_bonus(caster, "wis", bonus=1) == 6
    assert spell_save_dc(caster, "wis", bonus=1) == 14


def test_spell_slot_state_spends_and_restores_slots_by_level() -> None:
    slots = create_spell_slots({1: 4, 2: 3})

    after_first = spend_spell_slot(slots, 1)
    after_second = spend_spell_slot(after_first, 2)
    restored = restore_spell_slots(after_second)

    assert tuple(slot.level for slot in slots.slots) == (1, 2)
    assert spell_slots_remaining(after_first, 1) == 3
    assert spell_slots_remaining(after_first, 2) == 3
    assert spell_slots_remaining(after_second, 2) == 2
    assert restored.slots == slots.slots


def test_spell_slot_state_rejects_invalid_or_unavailable_slots() -> None:
    with pytest.raises(ValueError, match="spell slot level"):
        SpellSlotPool(level=0, maximum=1, remaining=1)

    with pytest.raises(ValueError, match="maximum spell slots"):
        SpellSlotPool(level=1, maximum=0, remaining=0)

    with pytest.raises(ValueError, match="remaining spell slots"):
        SpellSlotPool(level=1, maximum=1, remaining=2)

    with pytest.raises(ValueError, match="duplicate spell slot level"):
        SpellSlotState(
            (
                SpellSlotPool(level=1, maximum=1, remaining=1),
                SpellSlotPool(level=1, maximum=1, remaining=1),
            )
        )

    with pytest.raises(ValueError, match="no spell slots remaining for level 2"):
        spend_spell_slot(create_spell_slots({1: 1}), 2)

    with pytest.raises(ValueError, match="no spell slots remaining for level 1"):
        spend_spell_slot(SpellSlotState((SpellSlotPool(level=1, maximum=1, remaining=0),)), 1)


def test_pact_magic_state_spends_and_restores_shared_slots() -> None:
    pact_magic = create_pact_magic(slot_level=3, maximum=2)

    after_spend = spend_pact_slot(pact_magic)
    restored = restore_pact_magic(after_spend)

    assert pact_magic.slot_level == 3
    assert after_spend.remaining == 1
    assert restored.remaining == 2
    assert restored.maximum == 2


def test_pact_magic_state_rejects_invalid_or_unavailable_slots() -> None:
    with pytest.raises(ValueError, match="pact magic slot level"):
        PactMagicState(slot_level=6, maximum=2, remaining=2)

    with pytest.raises(ValueError, match="maximum pact magic slots"):
        PactMagicState(slot_level=1, maximum=0, remaining=0)

    with pytest.raises(ValueError, match="remaining pact magic slots"):
        PactMagicState(slot_level=1, maximum=1, remaining=2)

    with pytest.raises(ValueError, match="no pact magic slots remaining"):
        spend_pact_slot(PactMagicState(slot_level=1, maximum=1, remaining=0))


def test_saving_throw_resolves_against_spell_dc() -> None:
    result = saving_throw(ability="dex", save_bonus=2, dc=13, roll=11)

    assert result.roll == 11
    assert result.total == 13
    assert result.success is True


def test_spell_attack_applies_damage_on_hit() -> None:
    combat = simple_spell_combat()

    result = resolve_spell_attack(
        combat,
        actor_id="wizard",
        target_id="goblin",
        attack_bonus=6,
        damage_dice="1d10",
        damage_type="fire",
        roll=12,
        damage_rng=lambda: 0,
    )

    assert result.hit
    assert result.damage is not None
    assert result.damage.total == 1
    assert combatant_by_id(result.state, "goblin").hit_points.current == 6


def test_spell_save_damage_applies_full_damage_on_failed_save() -> None:
    combat = simple_spell_combat()

    result = resolve_spell_save_damage(
        combat,
        target_id="goblin",
        save_ability="dex",
        save_bonus=2,
        save_dc=13,
        damage_dice="1d8",
        damage_type="radiant",
        roll=8,
        damage_rng=lambda: 0,
    )

    assert result.save.success is False
    assert result.damage is not None
    assert result.damage.total == 1
    assert result.damage_application is not None
    assert result.damage_application.applied_to_current == 1
    assert result.target_after.hit_points.current == 6


def test_spell_save_damage_can_skip_or_half_damage_on_success() -> None:
    combat = simple_spell_combat()

    avoided = resolve_spell_save_damage(
        combat,
        target_id="goblin",
        save_ability="dex",
        save_bonus=5,
        save_dc=13,
        damage_dice="1d8",
        damage_type="radiant",
        roll=10,
    )
    halved = resolve_spell_save_damage(
        combat,
        target_id="goblin",
        save_ability="dex",
        save_bonus=5,
        save_dc=13,
        damage_dice="1d8",
        damage_type="radiant",
        roll=10,
        damage_rng=lambda: 0.99,
        half_damage_on_success=True,
    )

    assert avoided.damage is None
    assert avoided.target_after.hit_points.current == 7
    assert halved.damage is not None
    assert halved.damage.total == 8
    assert halved.damage_application is not None
    assert halved.damage_application.applied_to_current == 4
    assert halved.target_after.hit_points.current == 3


def test_spell_healing_rolls_dice_and_applies_healing() -> None:
    combat = simple_spell_combat()
    damaged = resolve_spell_save_damage(
        combat,
        target_id="wizard",
        save_ability="dex",
        save_bonus=0,
        save_dc=12,
        damage_dice="1d8",
        damage_type="necrotic",
        roll=1,
        damage_rng=lambda: 0.99,
    )

    result = apply_spell_healing(
        damaged.state,
        target_id="wizard",
        healing_dice="1d8+3",
        healing_rng=lambda: 0,
    )

    assert result.roll.total == 4
    assert result.healing.applied == 4
    assert result.target_after.hit_points.current == 16


def test_spell_condition_applies_directly_or_after_failed_save() -> None:
    combat = simple_spell_combat()

    direct = apply_spell_condition(combat, target_id="goblin", condition="blinded")
    resisted = apply_spell_condition(
        combat,
        target_id="goblin",
        condition="poisoned",
        save_ability="con",
        save_bonus=4,
        save_dc=12,
        roll=10,
    )
    failed = apply_spell_condition(
        combat,
        target_id="goblin",
        condition="poisoned",
        save_ability="con",
        save_bonus=0,
        save_dc=12,
        roll=5,
    )

    assert direct.applied is True
    assert direct.target_after.conditions == ("blinded",)
    assert resisted.applied is False
    assert resisted.target_after.conditions == ()
    assert failed.applied is True
    assert failed.target_after.conditions == ("poisoned",)


def test_spell_effect_helpers_validate_saves() -> None:
    with pytest.raises(ValueError, match="saving throw DC must be positive"):
        saving_throw(ability="wis", save_bonus=1, dc=0, roll=10)

    with pytest.raises(ValueError, match="save_dc is required"):
        apply_spell_condition(
            simple_spell_combat(),
            target_id="goblin",
            condition="restrained",
            save_ability="str",
        )


def simple_spell_combat():
    return create_combat(
        [
            create_combatant(
                id="wizard",
                name="Wizard",
                initiative_bonus=2,
                roll=12,
                armor_class=12,
                hit_points=HitPointState(current=20, maximum=20),
            ),
            create_combatant(
                id="goblin",
                name="Goblin",
                initiative_bonus=2,
                roll=10,
                armor_class=15,
                hit_points=HitPointState(current=7, maximum=7),
            ),
        ]
    )
