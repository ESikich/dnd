from __future__ import annotations

from random import Random
from collections.abc import Callable
from typing import NamedTuple, cast

from dnd5e import (
    ARMOR,
    CONDITIONS,
    CREATURES,
    FEATURES,
    SKILL_ABILITIES,
    SPELLS,
    SRD_CLASSES,
    SHIELDS,
    ArmorClassModifier,
    CharacterClassLevel,
    CharacterLoadout,
    CharacterRules,
    CharacterSheet,
    ConditionName,
    CreatureFeature,
    DamageType,
    DiceRoll,
    HitPointState,
    ProficiencyLevel,
    Skill,
    TurnEffect,
    WEAPONS,
    Ability,
    ability_bonus,
    ability_modifier,
    apply_combat_damage,
    apply_condition,
    apply_healing,
    apply_second_wind,
    apply_spell_condition,
    apply_spell_healing,
    apply_turn_effects,
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
    concentration_check,
    condition_attack_modifier,
    create_combat,
    create_combatant,
    create_creature_instance,
    create_hit_dice_pool,
    create_feature_state,
    create_pact_magic,
    create_spell_slots,
    creature_action_recharge_state,
    creature_runtime_combatant,
    d20_check,
    damage_roll,
    encounter_monster,
    initiative_bonus,
    load_builtin_class_pack,
    load_builtin_condition_pack,
    load_builtin_creature_pack,
    load_builtin_equipment_pack,
    load_builtin_feature_pack,
    load_builtin_spell_pack,
    long_rest,
    modified_armor_class,
    recharge_feature,
    next_turn,
    parse_dice_notation,
    passive_score,
    passive_skill,
    proficiency_bonus,
    proficiency_value,
    resolve_attack_action,
    resolve_spell_attack,
    resolve_spell_save_damage,
    restore_pact_magic,
    roll_dice,
    saving_throw_bonus,
    short_rest,
    short_rest_feature,
    skill_bonus,
    sneak_attack_damage,
    sneak_attack_damage_dice,
    spell_attack_bonus,
    spell_save_dc,
    spell_slots_remaining,
    spend_feature_resource,
    spend_pact_slot,
    spend_spell_slot,
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
    show_effects_and_conditions()
    show_resource_features()
    show_spell_catalog()
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
    abilities: tuple[Ability, ...] = ("str", "dex", "con", "int", "wis", "cha")
    for ability in abilities:
        print(f"  {ability.upper()}: {ability_bonus(hero, ability):+d}")

    print("\nSkill map sample:")
    skills: tuple[Skill, ...] = ("athletics", "perception", "stealth", "survival")
    for skill in skills:
        print(
            f"  {skill:<10} uses {SKILL_ABILITIES[skill].upper()} "
            f"-> bonus {skill_bonus(hero, skill):+d}, passive {passive_skill(hero, skill)}"
        )

    print("\nSaving throws:")
    saving_throws: tuple[Ability, ...] = ("str", "dex", "con", "wis")
    for ability in saving_throws:
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
            skill_proficiencies=cast(dict[Skill, ProficiencyLevel], {"tactics": "proficient"}),
            loadout=CharacterLoadout(armor="chain_mail", weapons=("spoon",)),
        )
    except ValueError as error:
        print(f"Invalid sheet rejected: {error}")


def show_equipment(hero: CharacterRules) -> None:
    print_section("Equipment")

    equipment_pack = load_builtin_equipment_pack()
    armor = ARMOR["chain_mail"]
    shield = SHIELDS["shield"]
    ac = armor_class(hero, armor=armor, shield=shield)
    print(
        f"Built-in equipment pack: {len(equipment_pack.armor)} armor, "
        f"{len(equipment_pack.shields)} shields, {len(equipment_pack.weapons)} weapons"
    )
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

    class_pack = load_builtin_class_pack()
    condition_pack = load_builtin_condition_pack()
    fighter = SRD_CLASSES["fighter"]
    wizard = SRD_CLASSES["wizard"]
    print(f"Built-in class pack: {len(class_pack.classes)} classes")
    print(f"Built-in condition pack: {len(condition_pack.conditions)} conditions")
    print(
        f"Fighter: d{fighter.hit_die} hit die, saves {join_upper(fighter.saving_throws)}, "
        f"armor {', '.join(fighter.armor_training)}"
    )
    print(
        f"Wizard: d{wizard.hit_die} hit die, primary {join_upper(wizard.primary_abilities)}, "
        f"skill picks {wizard.skill_choice_count}"
    )

    condition_names: tuple[ConditionName, ...] = ("blinded", "grappled", "poisoned", "unconscious")
    for name in condition_names:
        condition = CONDITIONS[name]
        print(f"Condition {name}: {', '.join(condition.tags)}")


def show_effects_and_conditions() -> None:
    print_section("Effects And Conditions")

    combat = create_combat(
        [
            create_combatant(
                id="hero",
                name="Kara",
                initiative_bonus=2,
                roll=14,
                armor_class=18,
                hit_points=HitPointState(current=20, maximum=20),
            ),
            creature_runtime_combatant(create_creature_instance("skeleton"), roll=12),
        ]
    )
    restrained = apply_condition(combat, target_id="skeleton", condition="restrained")
    poison_modifier = condition_attack_modifier(attacker_conditions=("poisoned",))
    shield_spell = ArmorClassModifier(bonus=5, reason="shield")
    shielded_ac = modified_armor_class(15, (shield_spell,))
    bludgeoning = apply_combat_damage(
        restrained,
        target_id="skeleton",
        amount=4,
        damage_type="bludgeoning",
    )
    poisoned = apply_condition(combat, target_id="hero", condition="poisoned")
    turn_effects = (
        TurnEffect(name="ongoing fire", timing="start", damage=3, damage_type="fire"),
        TurnEffect(name="poison ends", timing="end", remove_conditions=("poisoned",)),
    )
    scorched = apply_turn_effects(poisoned, target_id="hero", timing="start", effects=turn_effects)
    recovered = apply_turn_effects(scorched.state, target_id="hero", timing="end", effects=turn_effects)
    concentration = concentration_check(save_bonus=5, damage_taken=22, roll=7)

    adjustment = bludgeoning.damage_adjustment
    assert adjustment is not None
    print(f"Poisoned attack modifier: {poison_modifier.advantage}")
    print(f"Shield-style AC hook: {shielded_ac.base} -> {shielded_ac.total}")
    print(f"Skeleton conditions: {combatant_by_id(restrained, 'skeleton').conditions}")
    print(
        f"Bludgeoning skeleton: {adjustment.original} -> {adjustment.adjusted} "
        f"({', '.join(adjustment.modifiers)})"
    )
    print(
        f"Turn hooks: start damage {scorched.applications[0].damage_applied}, "
        f"end conditions {combatant_by_id(recovered.state, 'hero').conditions}"
    )
    print(f"Concentration check: DC {concentration.dc}, total {concentration.total}, broken={concentration.broken}")


def show_resource_features() -> None:
    print_section("Resources And Features")

    feature_pack = load_builtin_feature_pack()
    second_wind = create_feature_state(FEATURES["second_wind"])
    spent_second_wind = spend_feature_resource(second_wind)
    rested_second_wind = short_rest_feature(spent_second_wind)
    second_wind_healing = apply_second_wind(
        create_feature_state(FEATURES["second_wind"]),
        HitPointState(current=12, maximum=20),
        fighter_level=5,
        roll=6,
    )
    sneak_attack = sneak_attack_damage(rogue_level=5, damage_type="piercing", rng=lambda: 0)
    recharge = create_feature_state(FEATURES["recharge_5_6"], remaining=0)
    recharged, recharge_roll = recharge_feature(recharge, roll=5)
    proficiency_uses = create_feature_state(FEATURES["proficiency_uses"], level=9)

    assert spent_second_wind.resource is not None
    assert rested_second_wind.resource is not None
    assert recharged.resource is not None
    assert proficiency_uses.resource is not None

    print(f"Built-in feature pack: {len(feature_pack.features)} features")
    print(
        f"{second_wind.definition.name}: "
        f"{spent_second_wind.resource.remaining}/{spent_second_wind.resource.maximum} after use, "
        f"{rested_second_wind.resource.remaining}/{rested_second_wind.resource.maximum} after short rest"
    )
    print(
        f"Second Wind healing: roll {second_wind_healing.roll} + fighter level 5 "
        f"-> {second_wind_healing.healing.applied} HP restored"
    )
    print(
        f"Sneak Attack level 5: {sneak_attack_damage_dice(5)} bonus damage "
        f"-> {sneak_attack.total} {sneak_attack.type}"
    )
    print(
        f"{recharge.definition.name}: roll {recharge_roll.roll}, "
        f"recharged={recharge_roll.recharged}, remaining {recharged.resource.remaining}"
    )
    print(
        f"Level 9 proficiency-based uses: "
        f"{proficiency_uses.resource.remaining}/{proficiency_uses.resource.maximum}"
    )


def show_spell_catalog() -> None:
    print_section("Spells")

    spell_pack = load_builtin_spell_pack()
    wizard = CharacterRules(
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

    print(f"Built-in spell pack: {len(spell_pack.spells)} spells")
    for spell_id in ["fire_bolt", "cure_wounds", "detect_magic", "mage_armor"]:
        spell = SPELLS[spell_id]
        flags = []
        if spell.concentration:
            flags.append("concentration")
        if spell.ritual:
            flags.append("ritual")
        suffix = f" ({', '.join(flags)})" if flags else ""
        print(
            f"{spell.name}: level {spell.level} {spell.school}, "
            f"{spell.casting_time}, range {spell.range}, duration {spell.duration}{suffix}"
        )
    print(
        f"Level {wizard.level} wizard spell attack {spell_attack_bonus(wizard, 'int'):+d}, "
        f"spell save DC {spell_save_dc(wizard, 'int')}"
    )

    slots = create_spell_slots({1: 4, 2: 3, 3: 2})
    slots = spend_spell_slot(slots, 3)
    pact_magic = spend_pact_slot(create_pact_magic(slot_level=2, maximum=2))
    pact_magic = restore_pact_magic(pact_magic)
    print(
        f"After casting a 3rd-level spell: {spell_slots_remaining(slots, 3)} level-3 slots remain; "
        f"rested pact slots at level {pact_magic.slot_level}: {pact_magic.remaining}/{pact_magic.maximum}"
    )

    spell_combat = create_combat(
        [
            create_combatant(
                id="wizard",
                name="Apprentice Wizard",
                initiative_bonus=2,
                roll=12,
                armor_class=12,
                hit_points=HitPointState(current=8, maximum=12),
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
    fire_bolt = resolve_spell_attack(
        spell_combat,
        actor_id="wizard",
        target_id="goblin",
        attack_bonus=spell_attack_bonus(wizard, "int"),
        damage_dice="1d10",
        damage_type="fire",
        roll=12,
        damage_rng=lambda: 0,
    )
    sacred_flame = resolve_spell_save_damage(
        spell_combat,
        target_id="goblin",
        save_ability="dex",
        save_bonus=2,
        save_dc=spell_save_dc(wizard, "int"),
        damage_dice="1d8",
        damage_type="radiant",
        roll=8,
        damage_rng=lambda: 0,
    )
    healed = apply_spell_healing(
        spell_combat,
        target_id="wizard",
        healing_dice="1d8+3",
        healing_rng=lambda: 0,
    )
    blinded = apply_spell_condition(
        spell_combat,
        target_id="goblin",
        condition="blinded",
        save_ability="con",
        save_bonus=0,
        save_dc=spell_save_dc(wizard, "int"),
        roll=5,
    )
    print(
        f"Fire Bolt hit: {fire_bolt.hit}; "
        f"Sacred Flame save {sacred_flame.save.total} vs DC {sacred_flame.save.dc}, "
        f"Goblin HP {sacred_flame.target_after.hit_points.current}"
    )
    print(
        f"Cure Wounds style healing restores {healed.healing.applied}; "
        f"condition applied: {blinded.condition}={blinded.applied}"
    )


def show_creature_catalog() -> None:
    print_section("Creature Catalog")

    creature_pack = load_builtin_creature_pack()
    goblin = CREATURES["goblin"]
    wolf = CREATURES["wolf"]
    skeleton = CREATURES["skeleton"]
    zombie = CREATURES["zombie"]
    orc = CREATURES["orc"]
    black_bear = CREATURES["black_bear"]
    bugbear = CREATURES["bugbear"]
    ghoul = CREATURES["ghoul"]
    giant_spider = CREATURES["giant_spider"]
    gray_ooze = CREATURES["gray_ooze"]
    ogre = CREATURES["ogre"]

    print(f"Built-in creature pack: {len(creature_pack.creatures)} creatures")
    print(
        f"{goblin.name}: CR {goblin.challenge_rating}, XP {goblin.xp}, "
        f"bonus actions {join_names(goblin.bonus_actions)}"
    )
    print(f"{wolf.name}: traits {join_names(wolf.traits)}")
    print(f"{zombie.name}: traits {join_names(zombie.traits)}, speed {zombie.speed['walk']}")
    print(
        f"{skeleton.name}: vulnerable {', '.join(skeleton.damage_vulnerabilities)}, "
        f"immune {', '.join(skeleton.damage_immunities)}, "
        f"condition immune {', '.join(skeleton.condition_immunities)}"
    )
    print(
        f"{orc.name}: bonus actions {join_names(orc.bonus_actions)}, "
        f"attacks {', '.join(action.name for action in orc.actions)}"
    )
    print(
        f"{black_bear.name}: speed {black_bear.speed['walk']}, climb {black_bear.speed['climb']}, "
        f"traits {join_names(black_bear.traits)}"
    )
    print(f"{bugbear.name}: traits {join_names(bugbear.traits)}, stealth {bugbear.skills['stealth']:+d}")
    print(
        f"{ghoul.name}: immune {', '.join(ghoul.damage_immunities)}, "
        f"condition immune {', '.join(ghoul.condition_immunities)}"
    )
    print(
        f"{giant_spider.name}: CR {giant_spider.challenge_rating}, "
        f"traits {join_names(giant_spider.traits)}, "
        f"{giant_spider.actions[1].name} recharge {giant_spider.actions[1].recharge_minimum}-6"
    )
    print(
        f"{gray_ooze.name}: resists {', '.join(gray_ooze.damage_resistances)}, "
        f"condition immune {', '.join(gray_ooze.condition_immunities)}"
    )
    print(
        f"{ogre.name}: CR {ogre.challenge_rating}, HP {ogre.hit_points}, "
        f"attacks {', '.join(action.name for action in ogre.actions)}"
    )


def show_encounter_summary() -> None:
    print_section("Encounter Summary")

    encounter = summarize_encounter(
        [
            encounter_monster("ogre"),
            encounter_monster("bandit", count=2),
        ],
        party_levels=[3, 3, 3, 3],
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
    damage_type: DamageType
    damage_rng: Callable[[], float]


def show_battle() -> None:
    print_section("A Tiny Battle")

    kara = build_hero_sheet()
    kara_weapon = character_sheet_weapon_profile(kara, "longsword")
    goblin = create_creature_instance(CREATURES["goblin"])
    goblin_action = goblin.definition.actions[0]
    if goblin_action.damage_dice is None or goblin_action.damage_type is None:
        raise RuntimeError("scripted goblin action must deal damage")

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
    show_creature_recharge_example()


def show_creature_recharge_example() -> None:
    print_section("Creature Recharge")

    web = CREATURES["giant_spider"].actions[1]
    web_recharge = creature_action_recharge_state(web, remaining=0)
    recharged, result = recharge_feature(web_recharge, roll=5)

    assert recharged.resource is not None
    print(
        f"{web.name}: roll {result.roll}, recharged={result.recharged}, "
        f"uses {recharged.resource.remaining}/{recharged.resource.maximum}"
    )


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
