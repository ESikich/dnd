from __future__ import annotations

from random import Random
from collections.abc import Callable
from typing import NamedTuple

from dnd5e import (
    ARMOR,
    CONDITIONS,
    CREATURES,
    SKILL_ABILITIES,
    SRD_CLASSES,
    SHIELDS,
    CharacterClassLevel,
    CharacterLoadout,
    CharacterRules,
    CharacterSheet,
    CreatureFeature,
    DiceRoll,
    HitPointState,
    WEAPONS,
    ability_bonus,
    ability_modifier,
    apply_healing,
    armor_class,
    attack_roll,
    average_dice,
    character_sheet_armor_class,
    character_sheet_combatant,
    character_sheet_hit_points,
    character_sheet_initiative_bonus,
    character_sheet_weapon_profile,
    combatant_by_id,
    combatant_defeated,
    create_hit_dice_pool,
    create_combat,
    create_creature_instance,
    creature_runtime_combatant,
    d20_check,
    damage_roll,
    encounter_monster,
    initiative_bonus,
    long_rest,
    next_turn,
    parse_dice_notation,
    passive_score,
    passive_skill,
    proficiency_bonus,
    proficiency_value,
    resolve_attack_action,
    roll_dice,
    saving_throw_bonus,
    short_rest,
    skill_bonus,
    summarize_encounter,
    weapon_attack_profile,
)


def main() -> None:
    rng = Random(20260624)

    print_title("D&D 5E Rules Library Demo")
    show_core_math()
    show_dice(rng)
    hero = build_hero()
    show_character(hero)
    show_character_sheet(build_hero_sheet())
    show_sheet_validation()
    show_equipment(hero)
    show_class_and_condition_data()
    show_creature_catalog()
    show_encounter_summary()
    show_combat(rng, hero)


def show_core_math() -> None:
    print_section("Core Math")

    scores = [8, 10, 13, 16, 20]
    print("Ability modifiers:")
    for score in scores:
        print(f"  {score:>2}: {ability_modifier(score):+d}")

    print("\nProficiency by tier:")
    for level in [1, 5, 9, 13, 17, 20]:
        print(f"  Level {level:>2}: +{proficiency_bonus(level)}")

    check = d20_check(
        ability_score=16,
        proficiency_bonus_value=proficiency_bonus(5),
        proficiency="proficient",
        bonus=1,
        roll=12,
    )
    print(
        "\nAthletics check:"
        f" d20 {check.roll} + mod {check.modifier} + prof {check.proficiency}"
        f" + bonus {check.bonus} = {check.total}"
    )
    print(f"Passive version of the same modifier stack: {passive_score(check.modifier, check.proficiency, check.bonus)}")
    print(f"Expertise value at level 5: +{proficiency_value('expertise', proficiency_bonus(5))}")


def show_dice(rng: Random) -> None:
    print_section("Dice")

    for notation in ["d20", "2d6+3", "1d8+4", "4d6-1"]:
        parsed = parse_dice_notation(notation)
        rolled = roll_dice(notation, rng=rng.random)
        print(
            f"{notation:<6} -> count={parsed.count}, sides={parsed.sides}, modifier={parsed.modifier:+d}; "
            f"rolls={rolled.rolls}, total={rolled.total}, average={average_dice(notation):.1f}"
        )


def build_hero() -> CharacterRules:
    return CharacterRules(
        level=5,
        abilities={
            "str": 16,
            "dex": 14,
            "con": 14,
            "int": 10,
            "wis": 12,
            "cha": 8,
        },
        skill_proficiencies={
            "athletics": "expertise",
            "perception": "proficient",
            "survival": "proficient",
        },
        saving_throw_proficiencies={
            "str": "proficient",
            "con": "proficient",
        },
        skill_bonuses={"perception": 1},
        initiative_bonus_value=1,
    )


def build_hero_sheet() -> CharacterSheet:
    return CharacterSheet(
        id="hero",
        name="Kara",
        classes=(CharacterClassLevel("fighter", 5),),
        abilities={
            "str": 16,
            "dex": 14,
            "con": 14,
            "int": 10,
            "wis": 12,
            "cha": 8,
        },
        skill_proficiencies={
            "athletics": "expertise",
            "perception": "proficient",
            "survival": "proficient",
        },
        saving_throw_proficiencies={
            "str": "proficient",
            "con": "proficient",
        },
        skill_bonuses={"perception": 1},
        initiative_bonus_value=1,
        loadout=CharacterLoadout(
            armor="chain_mail",
            shield="shield",
            weapons=("longsword", "shortbow"),
        ),
    )


def show_character(hero: CharacterRules) -> None:
    print_section("Character Helpers")

    print(f"Level: {hero.level}, proficiency bonus: +{proficiency_bonus(hero.level)}")
    print("Ability bonuses:")
    for ability in ["str", "dex", "con", "int", "wis", "cha"]:
        print(f"  {ability.upper()}: {ability_bonus(hero, ability):+d}")

    print("\nSkill map sample:")
    for skill in ["athletics", "perception", "stealth", "survival"]:
        print(
            f"  {skill:<10} uses {SKILL_ABILITIES[skill].upper()} "
            f"-> bonus {skill_bonus(hero, skill):+d}, passive {passive_skill(hero, skill)}"
        )

    print("\nSaving throws:")
    for ability in ["str", "dex", "con", "wis"]:
        print(f"  {ability.upper()}: {saving_throw_bonus(hero, ability):+d}")

    print(f"\nInitiative bonus: {initiative_bonus(hero):+d}")


def show_character_sheet(sheet: CharacterSheet) -> None:
    print_section("Character Sheet")

    ac = character_sheet_armor_class(sheet)
    hp = character_sheet_hit_points(sheet)
    weapon = character_sheet_weapon_profile(sheet, "longsword")

    print(
        f"{sheet.name}: level {sheet.classes[0].level} {sheet.classes[0].name}, "
        f"AC {ac.total}, HP {hp.maximum}, initiative {character_sheet_initiative_bonus(sheet):+d}"
    )
    print(
        f"{weapon.weapon.name}: attack {weapon.attack_bonus:+d}, "
        f"damage {weapon.damage_dice}{weapon.damage_bonus:+d} {weapon.damage_type}"
    )


def show_sheet_validation() -> None:
    print_section("Sheet Validation")

    try:
        CharacterSheet(
            id="invalid",
            name="Invalid Hero",
            classes=(CharacterClassLevel("fighter", 1),),
            abilities={
                "str": 10,
                "dex": 10,
                "con": 10,
                "int": 10,
                "wis": 10,
                "cha": 10,
            },
            skill_proficiencies={"tactics": "proficient"},
            loadout=CharacterLoadout(armor="chain_mail", weapons=("spoon",)),
        )
    except ValueError as error:
        print(f"Invalid sheet rejected: {error}")


def show_equipment(hero: CharacterRules) -> None:
    print_section("Equipment")

    armor = ARMOR["chain_mail"]
    shield = SHIELDS["shield"]
    ac = armor_class(hero, armor=armor, shield=shield)
    print(
        f"{armor.name} and {shield.name}: AC {ac.total} "
        f"(base {ac.base}, dex {ac.dexterity_bonus:+d}, shield {ac.shield_bonus:+d})"
    )

    rapier = weapon_attack_profile(hero, WEAPONS["rapier"])
    longsword = weapon_attack_profile(hero, "longsword", two_handed=True)
    shortbow = weapon_attack_profile(hero, "shortbow")

    print(
        f"Rapier: {rapier.ability.upper()} attack {rapier.attack_bonus:+d}, "
        f"damage {rapier.damage_dice}{rapier.damage_bonus:+d} {rapier.damage_type}"
    )
    print(
        f"Longsword two-handed: {longsword.ability.upper()} attack {longsword.attack_bonus:+d}, "
        f"damage {longsword.damage_dice}{longsword.damage_bonus:+d} {longsword.damage_type}"
    )
    print(
        f"Shortbow: {shortbow.ability.upper()} attack {shortbow.attack_bonus:+d}, "
        f"damage {shortbow.damage_dice}{shortbow.damage_bonus:+d} {shortbow.damage_type}"
    )


def show_class_and_condition_data() -> None:
    print_section("Class And Condition Data")

    fighter = SRD_CLASSES["fighter"]
    wizard = SRD_CLASSES["wizard"]
    print(
        f"Fighter: d{fighter.hit_die} hit die, saves {join_upper(fighter.saving_throws)}, "
        f"armor {', '.join(fighter.armor_training)}"
    )
    print(
        f"Wizard: d{wizard.hit_die} hit die, primary {join_upper(wizard.primary_abilities)}, "
        f"skill picks {wizard.skill_choice_count}"
    )

    for name in ["blinded", "grappled", "poisoned", "unconscious"]:
        condition = CONDITIONS[name]
        print(f"Condition {name}: {', '.join(condition.tags)}")


def show_creature_catalog() -> None:
    print_section("Creature Catalog")

    goblin = CREATURES["goblin"]
    wolf = CREATURES["wolf"]
    skeleton = CREATURES["skeleton"]

    print(
        f"{goblin.name}: CR {goblin.challenge_rating}, XP {goblin.xp}, "
        f"bonus actions {join_names(goblin.bonus_actions)}"
    )
    print(f"{wolf.name}: traits {join_names(wolf.traits)}")
    print(
        f"{skeleton.name}: vulnerable {', '.join(skeleton.damage_vulnerabilities)}, "
        f"immune {', '.join(skeleton.damage_immunities)}, "
        f"condition immune {', '.join(skeleton.condition_immunities)}"
    )


def show_encounter_summary() -> None:
    print_section("Encounter Summary")

    encounter = summarize_encounter(
        [
            encounter_monster("goblin", count=3),
            encounter_monster("wolf"),
        ],
        party_levels=[1, 1, 1, 1],
    )

    print(
        f"Monsters {encounter.monster_count}, raw XP {encounter.total_xp}, "
        f"adjusted XP {encounter.adjusted_xp:g} (x{encounter.xp_multiplier:g})"
    )
    print(
        f"Party thresholds: easy {encounter.thresholds.easy}, medium {encounter.thresholds.medium}, "
        f"hard {encounter.thresholds.hard}, deadly {encounter.thresholds.deadly}"
    )
    print(f"Difficulty: {encounter.difficulty}")


def show_combat(rng: Random, hero: CharacterRules) -> None:
    print_section("Combat")

    combat = create_combat(
        [
            {
                "id": "hero",
                "name": "Kara the Fighter",
                "initiative_bonus": initiative_bonus(hero),
                "roll": 14,
            },
            {"id": "goblin", "name": "Goblin Skirmisher", "initiative_bonus": 2, "roll": 16},
            {"id": "adept", "name": "Cult Adept", "initiative_bonus": 1, "roll": 9},
        ]
    )

    print("Initiative order:")
    for index, combatant in enumerate(combat.order, start=1):
        marker = "<- current" if combatant == combat.current else ""
        print(f"  {index}. {combatant.name:<18} initiative {combatant.initiative:>2} {marker}")

    attack_bonus = ability_bonus(hero, "str") + proficiency_bonus(hero.level)
    attack = attack_roll(attacker_bonus=attack_bonus, target_armor_class=15, roll=18)
    damage = damage_roll(
        dice="1d8+3",
        bonus_dice=("1d6",),
        type="slashing",
        critical=attack.outcome == "critical-hit",
        rng=rng.random,
    )

    print(
        f"\nKara attacks AC {attack.target_armor_class}: natural {attack.roll}, "
        f"total {attack.total}, outcome {attack.outcome}"
    )
    print(f"Damage rolls: {format_damage_rolls(damage.rolls)} -> {damage.total} {damage.type}")

    critical = attack_roll(attacker_bonus=attack_bonus, target_armor_class=99, roll=20)
    critical_damage = damage_roll(dice="1d8+3", type="slashing", critical=True, rng=lambda: 0)
    print(
        f"Critical example: natural {critical.roll}, outcome {critical.outcome}, "
        f"damage notation {critical_damage.rolls[0].notation}, total {critical_damage.total}"
    )

    print("\nAdvancing turns:")
    state = combat
    for _ in range(4):
        print(f"  Round {state.round}, turn {state.turn_index + 1}: {state.current.name}")
        state = next_turn(state)

    show_battle()


class BattleAction(NamedTuple):
    actor_id: str
    target_id: str
    attack_bonus: int
    roll: int
    damage_dice: str
    damage_type: str
    damage_rng: Callable[[], float]


def show_battle() -> None:
    print_section("A Tiny Battle")

    kara = build_hero_sheet()
    kara_weapon = character_sheet_weapon_profile(kara, "longsword")
    goblin = create_creature_instance(CREATURES["goblin"])
    goblin_action = goblin.definition.actions[0]

    names = {
        "hero": "Kara",
        "goblin": "Goblin",
    }
    combat = create_combat(
        [
            character_sheet_combatant(
                kara,
                roll=14,
            ),
            creature_runtime_combatant(goblin, roll=16),
        ]
    )
    actions = [
        BattleAction("goblin", "hero", goblin_action.attack_bonus, 17, goblin_action.damage_dice, goblin_action.damage_type, fixed_rolls(0.49)),
        BattleAction(
            "hero",
            "goblin",
            kara_weapon.attack_bonus,
            13,
            f"{kara_weapon.damage_dice}+{kara_weapon.damage_bonus}",
            kara_weapon.damage_type,
            fixed_rolls(0.62),
        ),
        BattleAction("goblin", "hero", goblin_action.attack_bonus, 8, goblin_action.damage_dice, goblin_action.damage_type, fixed_rolls(0.33)),
        BattleAction(
            "hero",
            "goblin",
            kara_weapon.attack_bonus,
            20,
            f"{kara_weapon.damage_dice}+{kara_weapon.damage_bonus}",
            kara_weapon.damage_type,
            fixed_rolls(0.75, 0.25),
        ),
    ]

    print(
        "Opening HP: "
        f"Kara {combatant_by_id(combat, 'hero').hit_points.current}, "
        f"Goblin {combatant_by_id(combat, 'goblin').hit_points.current}"
    )
    print("Initiative:")
    for combatant in combat.order:
        print(f"  {combatant.name}: {combatant.initiative}")

    state = combat
    for action in actions:
        actor = combatant_by_id(state, action.actor_id)
        target = combatant_by_id(state, action.target_id)
        if combatant_defeated(actor) or combatant_defeated(target):
            break

        if state.current.id != action.actor_id:
            raise RuntimeError(f"script expected {action.actor_id}, got {state.current.id}")

        result = resolve_attack_action(
            state,
            actor_id=action.actor_id,
            target_id=action.target_id,
            attack_bonus=action.attack_bonus,
            damage_dice=action.damage_dice,
            damage_type=action.damage_type,
            roll=action.roll,
            damage_rng=action.damage_rng,
        )
        state = result.state

        print(
            f"\nRound {state.round}: {names[action.actor_id]} attacks {names[action.target_id]} "
            f"(roll {result.attack.roll}, total {result.attack.total} "
            f"vs AC {result.attack.target_armor_class}) -> {result.attack.outcome}"
        )

        if result.damage is not None:
            print(
                f"  Damage: {format_damage_rolls(result.damage.rolls)} = "
                f"{result.damage.total} {result.damage.type}; "
                f"{names[action.target_id]} HP {result.target_after.hit_points.current}"
            )
        else:
            print(f"  {names[action.target_id]} HP stays {result.target_after.hit_points.current}")

        state = next_turn(state)

    hero_hp = combatant_by_id(state, "hero").hit_points
    goblin_hp = combatant_by_id(state, "goblin").hit_points
    winner = "Kara" if goblin_hp.current == 0 else "Goblin" if hero_hp.current == 0 else "No one"
    print(
        f"\nResult: {winner} wins. Final HP: Kara {hero_hp.current}, "
        f"Goblin {goblin_hp.current}"
    )
    show_rest_example(hero_hp)


def show_rest_example(kara_hp: HitPointState) -> None:
    print_section("Rest And Recovery")

    hit_dice = create_hit_dice_pool(level=5, hit_die=10)
    healing = apply_healing(kara_hp, 4)
    short = short_rest(hit_dice, healing.hit_points, constitution_modifier=2, rolls=(6,))
    long = long_rest(short.hit_points, short.hit_dice)

    print(
        f"Second wind style healing: +{healing.applied}; "
        f"Kara HP {healing.hit_points.current}/{healing.hit_points.maximum}"
    )
    print(
        f"Short rest spends {short.hit_dice_spent}d10 and heals {short.healing}; "
        f"Kara HP {short.hit_points.current}/{short.hit_points.maximum}, "
        f"hit dice left {short.hit_dice[0].remaining}/{short.hit_dice[0].total}"
    )
    print(
        f"Long rest: Kara HP {long.hit_points.current}/{long.hit_points.maximum}, "
        f"hit dice left {long.hit_dice[0].remaining}/{long.hit_dice[0].total}"
    )


def format_damage_rolls(rolls: tuple[DiceRoll, ...]) -> str:
    return " + ".join(
        f"{roll.notation} {roll.rolls} {roll.modifier:+d}" for roll in rolls
    )


def join_upper(values: tuple[str, ...]) -> str:
    return ", ".join(value.upper() for value in values)


def join_names(values: tuple[CreatureFeature, ...]) -> str:
    return ", ".join(value.name for value in values) or "none"


def fixed_rolls(*values: float) -> Callable[[], float]:
    iterator = iter(values)

    def rng() -> float:
        return next(iterator)

    return rng


def print_title(title: str) -> None:
    print(title)
    print("=" * len(title))


def print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


if __name__ == "__main__":
    main()
