import pytest

from dnd5e import (
    HitPointState,
    MAGIC_ITEMS,
    MagicItemChargeState,
    MagicItemRechargeResult,
    active_magic_items,
    apply_magic_item_condition,
    combatant_by_id,
    create_combat,
    create_combatant,
    create_magic_item_charge_state,
    magic_item_armor_class_bonus,
    magic_item_extra_damage,
    magic_item_saving_throw_bonus,
    magic_item_spell_attack_bonus,
    magic_item_weapon_bonus,
    recharge_magic_item,
    spend_magic_item_charges,
)


def test_public_magic_item_runtime_imports_and_docstrings() -> None:
    assert MagicItemChargeState.__doc__
    assert MagicItemRechargeResult.__doc__
    assert MAGIC_ITEMS["mace_of_terror"].effects[0].condition == "frightened"


def test_active_magic_items_require_attunement_when_needed() -> None:
    active = active_magic_items(
        ("ring_of_protection", "weapon_1"),
        attuned_magic_items=("ring_of_protection",),
    )

    assert tuple(item.id for item in active) == ("ring_of_protection", "weapon_1")
    assert active_magic_items(("ring_of_protection",), attuned_magic_items=()) == ()


def test_magic_item_passive_bonuses_and_weapon_applicability() -> None:
    items = ("ring_of_protection", "weapon_1", "armor_1", "flame_tongue", "staff_of_power")

    assert magic_item_armor_class_bonus(items) == 4
    assert magic_item_saving_throw_bonus(items) == 3
    assert magic_item_spell_attack_bonus(items) == 2
    assert magic_item_weapon_bonus(items, "longsword") == 1
    assert magic_item_weapon_bonus(items, "quarterstaff") == 3
    assert magic_item_extra_damage(items, "longsword")[0].damage_dice == "2d6"
    assert magic_item_extra_damage(items, "mace") == ()


def test_magic_item_charge_state_spends_and_recharges() -> None:
    state = create_magic_item_charge_state("mace_of_terror")
    spent = spend_magic_item_charges(state)
    recharged = recharge_magic_item(spent, rng=lambda: 0.0)

    assert state.maximum == 3
    assert spent.remaining == 2
    assert recharged.roll_total == 1
    assert recharged.restored == 1
    assert recharged.state.remaining == 3

    with pytest.raises(ValueError, match="not enough charges"):
        spend_magic_item_charges(spent, charges=3)


def test_magic_item_condition_effect_applies_after_failed_save() -> None:
    combat = create_combat(
        [
            create_combatant(
                id="target",
                name="Target",
                initiative_bonus=0,
                roll=10,
                armor_class=12,
                hit_points=HitPointState(current=10, maximum=10),
            )
        ]
    )

    result = apply_magic_item_condition(
        combat,
        "mace_of_terror",
        target_id="target",
        save_bonus=0,
        roll=5,
    )

    assert result.applied is True
    assert result.save is not None
    assert result.save.dc == 15
    assert "frightened" in combatant_by_id(result.state, "target").conditions


def test_magic_item_charge_state_rejects_items_without_charges() -> None:
    with pytest.raises(ValueError, match="has no charges"):
        create_magic_item_charge_state("weapon_1")
