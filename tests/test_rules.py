from dnd5e import (
    SRD_CLASSES,
    CharacterRules,
    ability_modifier,
    attack_roll,
    average_dice,
    create_combat,
    d20_check,
    damage_roll,
    initiative_bonus,
    passive_skill,
    proficiency_bonus,
    roll_dice,
    saving_throw_bonus,
    skill_bonus,
)


def test_ability_modifiers() -> None:
    assert ability_modifier(1) == -5
    assert ability_modifier(10) == 0
    assert ability_modifier(18) == 4


def test_proficiency_by_level() -> None:
    assert proficiency_bonus(1) == 2
    assert proficiency_bonus(5) == 3
    assert proficiency_bonus(9) == 4
    assert proficiency_bonus(13) == 5
    assert proficiency_bonus(17) == 6


def test_d20_check() -> None:
    result = d20_check(
        ability_score=16,
        proficiency_bonus_value=2,
        proficiency="proficient",
        roll=12,
    )

    assert result.total == 17


def test_dice() -> None:
    result = roll_dice("2d6+3", rng=lambda: 0)

    assert result.rolls == (1, 1)
    assert result.total == 5
    assert average_dice("2d6+3") == 10


def test_character_helpers() -> None:
    character = CharacterRules(
        level=5,
        abilities={
            "str": 8,
            "dex": 16,
            "con": 14,
            "int": 10,
            "wis": 12,
            "cha": 10,
        },
        skill_proficiencies={"stealth": "expertise", "perception": "proficient"},
        saving_throw_proficiencies={"dex": "proficient"},
        initiative_bonus_value=1,
    )

    assert skill_bonus(character, "stealth") == 9
    assert passive_skill(character, "perception") == 14
    assert saving_throw_bonus(character, "dex") == 6
    assert initiative_bonus(character) == 4


def test_combat() -> None:
    combat = create_combat(
        [
            {"id": "a", "name": "Aria", "initiative_bonus": 2, "roll": 10},
            {"id": "b", "name": "Borin", "initiative_bonus": 1, "roll": 18},
        ]
    )

    assert combat.current.id == "b"


def test_attack_rolls() -> None:
    assert attack_roll(attacker_bonus=5, target_armor_class=15, roll=1).outcome == "critical-miss"
    assert attack_roll(attacker_bonus=5, target_armor_class=99, roll=20).outcome == "critical-hit"
    assert attack_roll(attacker_bonus=5, target_armor_class=15, roll=10).outcome == "hit"


def test_critical_damage_doubles_dice() -> None:
    result = damage_roll(dice="1d8+3", type="slashing", critical=True, rng=lambda: 0)

    assert result.rolls[0].notation == "2d8+3"
    assert result.total == 5


def test_class_metadata() -> None:
    assert SRD_CLASSES["fighter"].hit_die == 10
    assert SRD_CLASSES["wizard"].saving_throws == ("int", "wis")
