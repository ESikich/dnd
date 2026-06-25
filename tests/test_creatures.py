from pathlib import Path

import pytest

from dnd5e import (
    CREATURES,
    CreatureAction,
    CreatureDefinition,
    CreatureFeature,
    CreatureInstance,
    CreaturePack,
    create_creature_instance,
    creature_ability_bonus,
    creature_action_attack,
    creature_action_damage,
    creature_action_recharge_feature,
    creature_action_recharge_state,
    creature_combatant,
    creature_initiative_bonus,
    creature_skill_bonus,
    load_builtin_creature_pack,
    load_creature_pack,
    load_creature_pack_data,
    recharge_feature,
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


def _creature_action_entry(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "name": "Strike",
        "attack_bonus": 2,
        "damage_dice": "1d4",
        "damage_type": "bludgeoning",
        "reach": 5,
        "normal_range": None,
        "long_range": None,
        "target": "one target",
        "recharge_minimum": None,
        "recharge_die": 6,
    }
    values.update(overrides)
    return values


def _creature_pack_entry(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
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
        "languages": [],
        "challenge_rating": "0",
        "xp": 0,
        "actions": [_creature_action_entry()],
        "traits": [],
        "bonus_actions": [],
        "reactions": [],
        "damage_resistances": [],
        "damage_vulnerabilities": [],
        "damage_immunities": [],
        "condition_immunities": [],
        "legendary_actions": [],
    }
    values.update(overrides)
    return values


def test_public_creature_imports() -> None:
    assert isinstance(CREATURES["goblin"], CreatureDefinition)
    assert isinstance(CREATURES["goblin"].actions[0], CreatureAction)
    assert isinstance(CREATURES["goblin"].bonus_actions[0], CreatureFeature)
    assert isinstance(load_builtin_creature_pack(), CreaturePack)
    assert CreatureInstance is not None


def test_public_creature_dataclasses_have_docstrings() -> None:
    assert CreatureFeature.__doc__
    assert CreatureAction.__doc__
    assert CreatureDefinition.__doc__
    assert CreaturePack.__doc__
    assert CreatureInstance.__doc__


def test_builtin_creature_pack_loads_current_catalog() -> None:
    pack = load_builtin_creature_pack()

    assert pack.creatures == CREATURES
    assert len(pack.creatures) == 334
    assert pack.creatures["giant_spider"].actions[1].recharge_minimum == 5
    assert pack.creatures["skeleton"].damage_immunities == ("poison",)
    assert pack.creatures["skeleton"].condition_immunities == ("poisoned", "exhaustion")
    assert pack.creatures["adult_red_dragon"].legendary_actions[0].name == "Detect"
    assert pack.creatures["swarm_of_bats"].type == "swarm of Tiny beasts"
    assert pack.creatures["tarrasque"].source_url == "/api/2014/monsters/tarrasque"


def test_creature_pack_loads_from_decoded_data() -> None:
    pack = load_creature_pack_data(
        {
            "creatures": [
                {
                    "id": "spark_mephit",
                    "name": "Spark Mephit",
                    "size": "small",
                    "type": "elemental",
                    "alignment": "neutral",
                    "armor_class": 12,
                    "hit_points": 9,
                    "hit_dice": "2d6+2",
                    "speed": {"walk": 30, "fly": 30},
                    "abilities": {
                        "str": 6,
                        "dex": 14,
                        "con": 12,
                        "int": 8,
                        "wis": 10,
                        "cha": 10,
                    },
                    "saving_throws": {},
                    "skills": {"stealth": 4},
                    "senses": {"darkvision": 60, "passive_perception": 10},
                    "languages": ["Primordial"],
                    "challenge_rating": "1/4",
                    "xp": 50,
                    "actions": [
                        {
                            "name": "Claws",
                            "attack_bonus": 4,
                            "damage_dice": "1d4+2",
                            "damage_type": "slashing",
                            "reach": 5,
                            "normal_range": None,
                            "long_range": None,
                            "target": "one target",
                            "recharge_minimum": None,
                            "recharge_die": 6,
                        }
                    ],
                    "traits": [{"name": "Flicker", "tags": ["dim_light"]}],
                    "bonus_actions": [],
                    "reactions": [],
                    "damage_resistances": ["fire"],
                    "damage_vulnerabilities": [],
                    "damage_immunities": [],
                    "condition_immunities": [],
                }
            ]
        }
    )

    creature = pack.creatures["spark_mephit"]
    assert creature.speed["fly"] == 30
    assert creature.traits[0].tags == ("dim_light",)
    assert creature.damage_resistances == ("fire",)


def test_creature_pack_loads_json_file(tmp_path: Path) -> None:
    path = tmp_path / "creatures.json"
    path.write_text(
        """
        {
          "creatures": [
            {
              "id": "training_dummy",
              "name": "Training Dummy",
              "size": "medium",
              "type": "construct",
              "alignment": "unaligned",
              "armor_class": 10,
              "hit_points": 5,
              "hit_dice": "1d8+1",
              "speed": {"walk": 0},
              "abilities": {"str": 10, "dex": 10, "con": 10, "int": 1, "wis": 10, "cha": 1},
              "saving_throws": {},
              "skills": {},
              "senses": {"passive_perception": 10},
              "languages": [],
              "challenge_rating": "0",
              "xp": 0,
              "actions": [],
              "traits": [],
              "bonus_actions": [],
              "reactions": [],
              "damage_resistances": [],
              "damage_vulnerabilities": [],
              "damage_immunities": ["poison"],
              "condition_immunities": ["poisoned"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    pack = load_creature_pack(path)

    assert pack.creatures["training_dummy"].type == "construct"
    assert pack.creatures["training_dummy"].damage_immunities == ("poison",)


def test_creature_pack_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="missing sections"):
        load_creature_pack_data({})

    with pytest.raises(ValueError, match="unknown sections"):
        load_creature_pack_data({"creatures": [], "actions": []})

    with pytest.raises(ValueError, match="content section creatures must be a list"):
        load_creature_pack_data({"creatures": {}})

    with pytest.raises(ValueError, match="entries must be objects"):
        load_creature_pack_data({"creatures": ["goblin"]})

    with pytest.raises(ValueError, match="unknown fields"):
        load_creature_pack_data(
            {
                "creatures": [
                    {
                        **_creature_pack_entry(),
                        "text": "",
                    }
                ]
            }
        )

    with pytest.raises(ValueError, match="duplicate creature id"):
        load_creature_pack_data(
            {
                "creatures": [
                    _creature_pack_entry(),
                    _creature_pack_entry(),
                ]
            }
        )


def test_creature_pack_rejects_invalid_nested_entries() -> None:
    with pytest.raises(ValueError, match="creature.actions must be a list"):
        load_creature_pack_data({"creatures": [{**_creature_pack_entry(), "actions": {}}]})

    with pytest.raises(ValueError, match="creature.actions entries must be objects"):
        load_creature_pack_data({"creatures": [{**_creature_pack_entry(), "actions": ["Strike"]}]})

    with pytest.raises(ValueError, match="creature.actions entry has unknown fields"):
        load_creature_pack_data(
            {
                "creatures": [
                    {
                        **_creature_pack_entry(),
                        "actions": [{**_creature_action_entry(), "text": ""}],
                    }
                ]
            }
        )

    with pytest.raises(ValueError, match="creature feature.tags entries must be strings"):
        load_creature_pack_data(
            {
                "creatures": [
                    {
                        **_creature_pack_entry(),
                        "traits": [{"name": "Broken", "tags": [1]}],
                    }
                ]
            }
        )


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
    zombie = CREATURES["zombie"]

    assert [trait.name for trait in wolf.traits] == ["Keen Hearing and Smell", "Pack Tactics"]
    assert skeleton.damage_vulnerabilities == ("bludgeoning",)
    assert skeleton.damage_immunities == ("poison",)
    assert skeleton.condition_immunities == ("poisoned", "exhaustion")
    assert [trait.name for trait in zombie.traits] == ["Undead Fortitude"]
    assert zombie.damage_immunities == ("poison",)
    assert zombie.condition_immunities == ("poisoned",)


def test_creature_catalog_includes_more_srd_style_combatants() -> None:
    bandit = CREATURES["bandit"]
    kobold = CREATURES["kobold"]
    orc = CREATURES["orc"]
    axe_beak = CREATURES["axe_beak"]
    black_bear = CREATURES["black_bear"]
    bugbear = CREATURES["bugbear"]
    ghoul = CREATURES["ghoul"]
    giant_spider = CREATURES["giant_spider"]
    gray_ooze = CREATURES["gray_ooze"]
    ogre = CREATURES["ogre"]

    assert bandit.challenge_rating == "1/8"
    assert bandit.xp == 25
    assert bandit.actions[1].name == "Light Crossbow"
    assert bandit.actions[1].normal_range == 80
    assert "Pack Tactics" in [trait.name for trait in kobold.traits]
    assert kobold.actions[1].long_range == 120
    assert orc.challenge_rating == "1/2"
    assert orc.bonus_actions[0].name == "Aggressive"
    assert axe_beak.type == "beast"
    assert axe_beak.speed["walk"] == 50
    assert black_bear.challenge_rating == "1/2"
    assert black_bear.speed["climb"] == 30
    assert "Claws" in [action.name for action in black_bear.actions]
    assert bugbear.challenge_rating == "1"
    assert bugbear.skills["stealth"] == 6
    assert [trait.name for trait in bugbear.traits] == ["Brute", "Surprise Attack"]
    assert ghoul.type == "undead"
    assert ghoul.damage_immunities == ("poison",)
    assert ghoul.condition_immunities == ("poisoned", "charmed", "exhaustion")
    assert giant_spider.challenge_rating == "1"
    assert giant_spider.skills["stealth"] == 7
    assert [trait.name for trait in giant_spider.traits] == ["Spider Climb", "Web Sense", "Web Walker"]
    assert giant_spider.actions[1].name == "Web"
    assert giant_spider.actions[1].recharge_minimum == 5
    assert giant_spider.actions[1].damage_dice is None
    assert gray_ooze.type == "ooze"
    assert gray_ooze.damage_resistances == ("acid", "cold", "fire")
    assert gray_ooze.condition_immunities == (
        "blinded",
        "charmed",
        "deafened",
        "exhaustion",
        "frightened",
        "prone",
    )
    assert ogre.challenge_rating == "2"
    assert ogre.xp == 450
    assert ogre.size == "large"
    assert ogre.actions[0].damage_dice == "2d8+4"
    assert ogre.actions[1].long_range == 120


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


def test_creature_action_recharge_metadata_creates_feature_state() -> None:
    web = CREATURES["giant_spider"].actions[1]

    feature = creature_action_recharge_feature(web)
    state = creature_action_recharge_state(web, remaining=0)
    recharged, result = recharge_feature(state, roll=5)

    assert feature.id == "web_recharge"
    assert feature.resource is not None
    assert feature.resource.refresh == "recharge"
    assert feature.resource.recharge_minimum == 5
    assert state.resource is not None
    assert state.resource.remaining == 0
    assert result.recharged is True
    assert recharged.resource is not None
    assert recharged.resource.remaining == 1


def test_creature_action_rejects_invalid_dice() -> None:
    with pytest.raises(ValueError, match="invalid dice notation"):
        CreatureAction("Broken", 1, "flat 3", "slashing")


def test_creature_action_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="reach must be positive"):
        CreatureAction("Broken", 1, "1d4", "slashing", reach=0)

    with pytest.raises(ValueError, match="long_range"):
        CreatureAction("Broken", 1, "1d4", "slashing", normal_range=60, long_range=30)

    with pytest.raises(ValueError, match="recharge_minimum"):
        CreatureAction("Broken", 1, recharge_minimum=7)


def test_creature_action_damage_and_recharge_helpers_reject_unsupported_actions() -> None:
    web = CREATURES["giant_spider"].actions[1]

    with pytest.raises(ValueError, match="does not deal direct damage"):
        creature_action_damage(web)

    with pytest.raises(ValueError, match="provided together"):
        CreatureAction("Broken", 1, "1d4")

    with pytest.raises(ValueError, match="does not use recharge"):
        creature_action_recharge_feature(CREATURES["goblin"].actions[0])


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
