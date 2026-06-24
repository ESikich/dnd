import pytest

from dnd5e import (
    CREATURES,
    CreatureAction,
    CreatureDefinition,
    CreatureFeature,
    CreatureInstance,
    create_creature_instance,
    creature_ability_bonus,
    creature_action_attack,
    creature_action_damage,
    creature_combatant,
    creature_initiative_bonus,
    creature_skill_bonus,
)


def _creature_definition(**overrides: object) -> CreatureDefinition:
    values = {
        "id": "test",
        "name": "Test Creature",
        "size": "medium",
        "type": "humanoid",
        "alignment": "neutral",
        "armor_class": 12,
        "hit_points": 5,
        "hit_dice": "1d8+1",
        "speed": {"walk": 30},
        "abilities": {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10},
        "saving_throws": {},
        "skills": {},
        "senses": {"passive_perception": 10},
        "languages": (),
        "challenge_rating": "0",
        "xp": 0,
        "actions": (CreatureAction("Strike", 2, "1d4", "bludgeoning", reach=5),),
    }
    values.update(overrides)
    return CreatureDefinition(**values)  # type: ignore[arg-type]


def test_public_creature_imports() -> None:
    assert isinstance(CREATURES["goblin"], CreatureDefinition)
    assert isinstance(CREATURES["goblin"].actions[0], CreatureAction)
    assert isinstance(CREATURES["goblin"].bonus_actions[0], CreatureFeature)
    assert CreatureInstance is not None


def test_public_creature_dataclasses_have_docstrings() -> None:
    assert CreatureFeature.__doc__
    assert CreatureAction.__doc__
    assert CreatureDefinition.__doc__
    assert CreatureInstance.__doc__


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
    assert goblin.bonus_actions[0].name == "Nimble Escape"
    assert goblin.bonus_actions[0].tags == ("disengage", "hide")


def test_creature_catalog_includes_feature_and_immunity_metadata() -> None:
    wolf = CREATURES["wolf"]
    skeleton = CREATURES["skeleton"]

    assert [trait.name for trait in wolf.traits] == ["Keen Hearing and Smell", "Pack Tactics"]
    assert skeleton.damage_vulnerabilities == ("bludgeoning",)
    assert skeleton.damage_immunities == ("poison",)
    assert skeleton.condition_immunities == ("poisoned",)


def test_creature_feature_rejects_empty_names_and_tags() -> None:
    with pytest.raises(ValueError, match="feature name"):
        CreatureFeature("")

    with pytest.raises(ValueError, match="tags cannot be empty"):
        CreatureFeature("Broken", ("",))


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


def test_creature_action_rejects_invalid_dice() -> None:
    with pytest.raises(ValueError, match="invalid dice notation"):
        CreatureAction("Broken", 1, "flat 3", "slashing")


def test_creature_action_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="reach must be positive"):
        CreatureAction("Broken", 1, "1d4", "slashing", reach=0)

    with pytest.raises(ValueError, match="long_range"):
        CreatureAction("Broken", 1, "1d4", "slashing", normal_range=60, long_range=30)


def test_creature_definition_rejects_impossible_hp_ac_and_dice() -> None:
    with pytest.raises(ValueError, match="armor_class must be positive"):
        _creature_definition(armor_class=0)

    with pytest.raises(ValueError, match="hit_points must be positive"):
        _creature_definition(hit_points=0)

    with pytest.raises(ValueError, match="dice sides"):
        _creature_definition(hit_dice="1d1")


def test_creature_definition_rejects_invalid_ability_scores() -> None:
    with pytest.raises(ValueError, match="missing ability scores"):
        _creature_definition(abilities={"str": 10})

    with pytest.raises(ValueError, match="invalid abilities"):
        _creature_definition(
            abilities={"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10, "luck": 10}
        )

    with pytest.raises(ValueError, match="dex ability score"):
        _creature_definition(abilities={"str": 10, "dex": 31, "con": 10, "int": 10, "wis": 10, "cha": 10})


def test_creature_definition_rejects_invalid_bonus_keys() -> None:
    with pytest.raises(ValueError, match="invalid saving_throws"):
        _creature_definition(saving_throws={"luck": 2})

    with pytest.raises(ValueError, match="invalid skills"):
        _creature_definition(skills={"luck": 2})


def test_creature_definition_rejects_negative_movement_senses_and_xp() -> None:
    with pytest.raises(ValueError, match="speed.walk cannot be negative"):
        _creature_definition(speed={"walk": -5})

    with pytest.raises(ValueError, match="senses.passive_perception cannot be negative"):
        _creature_definition(senses={"passive_perception": -1})

    with pytest.raises(ValueError, match="xp cannot be negative"):
        _creature_definition(xp=-1)


def test_creature_definition_rejects_invalid_damage_and_condition_metadata() -> None:
    with pytest.raises(ValueError, match="invalid damage_resistances"):
        _creature_definition(damage_resistances=("water",))

    with pytest.raises(ValueError, match="invalid damage_vulnerabilities"):
        _creature_definition(damage_vulnerabilities=("water",))

    with pytest.raises(ValueError, match="invalid damage_immunities"):
        _creature_definition(damage_immunities=("water",))

    with pytest.raises(ValueError, match="invalid condition_immunities"):
        _creature_definition(condition_immunities=("sleepy",))
