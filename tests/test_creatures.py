from dnd5e import (
    CREATURES,
    CreatureAction,
    CreatureDefinition,
    CreatureInstance,
    create_creature_instance,
    creature_ability_bonus,
    creature_action_attack,
    creature_action_damage,
    creature_combatant,
    creature_initiative_bonus,
    creature_skill_bonus,
)


def test_public_creature_imports() -> None:
    assert isinstance(CREATURES["goblin"], CreatureDefinition)
    assert isinstance(CREATURES["goblin"].actions[0], CreatureAction)
    assert CreatureInstance is not None


def test_goblin_stat_block_values() -> None:
    goblin = CREATURES["goblin"]

    assert goblin.armor_class == 15
    assert goblin.hit_points == 7
    assert creature_ability_bonus(goblin, "dex") == 2
    assert creature_initiative_bonus(goblin) == 2
    assert creature_skill_bonus(goblin, "stealth") == 6
    assert goblin.actions[0].name == "Scimitar"
    assert goblin.actions[0].attack_bonus == 4
    assert goblin.actions[0].damage_dice == "1d6+2"


def test_creature_instance_initializes_hp_from_definition() -> None:
    instance = create_creature_instance("goblin", id="goblin-1")

    assert instance.id == "goblin-1"
    assert instance.definition is CREATURES["goblin"]
    assert instance.hit_points.current == 7
    assert instance.hit_points.maximum == 7


def test_creature_combatant_returns_existing_initiative_input_shape() -> None:
    instance = create_creature_instance("goblin", id="goblin-1")

    assert creature_combatant(instance, roll=16) == {
        "id": "goblin-1",
        "name": "Goblin",
        "initiative_bonus": 2,
        "roll": 16,
    }


def test_creature_action_attack_uses_existing_attack_roll_rules() -> None:
    action = CREATURES["goblin"].actions[0]

    assert creature_action_attack(action, target_ac=15, roll=10).outcome == "miss"
    assert creature_action_attack(action, target_ac=15, roll=11).outcome == "hit"
    assert creature_action_attack(action, target_ac=99, roll=20).outcome == "critical-hit"


def test_creature_action_damage_uses_existing_damage_roll_rules() -> None:
    action = CREATURES["goblin"].actions[0]

    normal = creature_action_damage(action, rng=lambda: 0)
    critical = creature_action_damage(action, critical=True, rng=lambda: 0)

    assert normal.rolls[0].notation == "1d6+2"
    assert normal.total == 3
    assert critical.rolls[0].notation == "2d6+2"
    assert critical.total == 4
