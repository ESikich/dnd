# D&D 5e Rules Library

A Python library for formalizing 5E-compatible rules, mechanics, combat,
character math, classes, creatures, equipment, HP, and conditions.

The first version is mechanics-first: it gives you typed primitives and rule
helpers without copying long-form rule text.

## Install

```sh
python -m pip install -e .
```

For development tools:

```sh
python -m pip install -e ".[dev]"
```

## Use

```py
from dnd5e import (
    CREATURES,
    FEATURES,
    CharacterClassLevel,
    CharacterLoadout,
    CharacterSheet,
    HitPointState,
    SPELLS,
    SRD_CLASSES,
    ability_modifier,
    apply_second_wind,
    apply_spell_condition,
    apply_spell_healing,
    attack_roll,
    character_sheet_armor_class,
    character_sheet_combatant,
    character_sheet_rules,
    character_sheet_weapon_profile,
    combatant_by_id,
    create_combat,
    create_combatant,
    create_creature_instance,
    create_feature_state,
    create_pact_magic,
    create_spell_slots,
    creature_action_recharge_state,
    d20_check,
    creature_runtime_combatant,
    recharge_feature,
    resolve_attack_action,
    resolve_spell_attack,
    resolve_spell_save_damage,
    restore_pact_magic,
    encounter_monster,
    summarize_encounter,
    roll_dice,
    short_rest_feature,
    sneak_attack_damage_dice,
    spell_attack_bonus,
    spell_save_dc,
    spell_slots_remaining,
    spend_feature_resource,
    spend_pact_slot,
    spend_spell_slot,
)

athletics = d20_check(
    ability_score=16,
    proficiency_bonus_value=2,
    proficiency="proficient",
    roll=12,
)

attack = attack_roll(attacker_bonus=5, target_armor_class=15, roll=10)

combat = create_combat(
    [
        create_combatant(
            id="fighter",
            name="Fighter",
            initiative_bonus=2,
            roll=15,
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

kara = CharacterSheet(
    id="kara",
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
    skill_proficiencies={"athletics": "expertise"},
    saving_throw_proficiencies={"str": "proficient", "con": "proficient"},
    loadout=CharacterLoadout(
        armor="chain_mail",
        shield="shield",
        weapons=("longsword",),
    ),
)
kara_ac = character_sheet_armor_class(kara)
kara_weapon = character_sheet_weapon_profile(kara, "longsword")
kara_combatant = character_sheet_combatant(kara, roll=14)
goblin = create_creature_instance(CREATURES["goblin"])
goblin_combatant = creature_runtime_combatant(goblin, roll=12)
skeleton = CREATURES["skeleton"]
zombie = CREATURES["zombie"]
orc = CREATURES["orc"]
black_bear = CREATURES["black_bear"]
bugbear = CREATURES["bugbear"]
ghoul = CREATURES["ghoul"]
giant_spider = CREATURES["giant_spider"]
gray_ooze = CREATURES["gray_ooze"]
ogre = CREATURES["ogre"]
fire_bolt = SPELLS["fire_bolt"]
detect_magic = SPELLS["detect_magic"]
spell_attack = spell_attack_bonus(character_sheet_rules(kara), "int")
spell_dc = spell_save_dc(character_sheet_rules(kara), "int")
spell_slots = spend_spell_slot(create_spell_slots({1: 4, 2: 3}), 2)
pact_magic = restore_pact_magic(spend_pact_slot(create_pact_magic(slot_level=2, maximum=2)))
second_wind = spend_feature_resource(create_feature_state(FEATURES["second_wind"]))
rested_second_wind = short_rest_feature(second_wind)
second_wind_healing = apply_second_wind(
    create_feature_state(FEATURES["second_wind"]),
    HitPointState(current=12, maximum=20),
    fighter_level=5,
    roll=6,
)
sneak_attack_dice = sneak_attack_damage_dice(5)
recharge_feature_state = create_feature_state(FEATURES["recharge_5_6"], remaining=0)
recharged_feature, recharge_roll = recharge_feature(recharge_feature_state, roll=5)
web_recharge_state = creature_action_recharge_state(giant_spider.actions[1], remaining=0)
recharged_web, web_recharge_roll = recharge_feature(web_recharge_state, roll=5)
encounter = summarize_encounter(
    [encounter_monster("ogre"), encounter_monster("bandit", count=2)],
    party_levels=[3, 3, 3, 3],
)

result = resolve_attack_action(
    combat,
    actor_id="fighter",
    target_id="goblin",
    attack_bonus=5,
    damage_dice="1d8+3",
    damage_type="slashing",
    roll=10,
    damage_rng=lambda: 0,
)

spell_hit = resolve_spell_attack(
    combat,
    actor_id="fighter",
    target_id="goblin",
    attack_bonus=spell_attack,
    damage_dice="1d10",
    damage_type="fire",
    roll=12,
    damage_rng=lambda: 0,
)
spell_save = resolve_spell_save_damage(
    combat,
    target_id="goblin",
    save_ability="dex",
    save_bonus=2,
    save_dc=spell_dc,
    damage_dice="1d8",
    damage_type="radiant",
    roll=8,
    damage_rng=lambda: 0,
)
spell_healing = apply_spell_healing(
    combat,
    target_id="fighter",
    healing_dice="1d8+3",
    healing_rng=lambda: 0,
)
spell_condition = apply_spell_condition(
    combat,
    target_id="goblin",
    condition="blinded",
    save_ability="con",
    save_bonus=0,
    save_dc=spell_dc,
    roll=5,
)

print(ability_modifier(16))  # 3
print(athletics.total)  # 17
print(combat.current.name)  # "Fighter"
print(result.attack.outcome)  # "hit"
print(combatant_by_id(result.state, "goblin").hit_points.current)  # 3
print(kara_ac.total)  # 18
print(kara_weapon.attack_bonus)  # 6
print(kara_combatant.hit_points.maximum)  # 44
print(goblin_combatant.armor_class)  # 15
print(skeleton.damage_immunities)  # ("poison",)
print(zombie.traits[0].name)  # "Undead Fortitude"
print(orc.bonus_actions[0].name)  # "Aggressive"
print(black_bear.speed["climb"])  # 30
print(bugbear.traits[0].name)  # "Brute"
print(ghoul.condition_immunities)  # ("charmed", "poisoned")
print(giant_spider.traits[0].name)  # "Spider Climb"
print(gray_ooze.damage_resistances)  # ("acid", "cold", "fire")
print(ogre.actions[0].damage_dice)  # "2d8+4"
print(fire_bolt.range)  # "120 feet"
print(detect_magic.ritual)  # True
print(spell_attack)  # 3
print(spell_dc)  # 11
print(spell_slots_remaining(spell_slots, 2))  # 2
print(pact_magic.remaining)  # 2
print(rested_second_wind.resource.remaining)  # 1
print(second_wind_healing.healing.applied)  # 8
print(sneak_attack_dice)  # "3d6"
print(recharge_roll.recharged)  # True
print(web_recharge_roll.recharged)  # True
print(spell_hit.damage.total)  # 1
print(spell_save.save.success)  # False
print(spell_healing.healing.applied)  # 0
print(spell_condition.applied)  # True
print(CREATURES["wolf"].traits[0].name)  # "Keen Hearing and Smell"
print(encounter.adjusted_xp)  # 1000
print(encounter.difficulty)  # "hard"
print(roll_dice("2d6+3").total)
print(SRD_CLASSES["fighter"].hit_die)  # 10
```

## Scope

Included now:

- Dice notation parsing and rolling
- Ability modifiers, proficiency bonuses, checks, saves, and passive scores
- Character skill and saving throw bonus helpers
- Initiative ordering and turn advancement
- Attack rolls, critical hit/miss handling, and damage rolling
- Combat runtime state with validated AC, HP, conditions, attack resolution, and healing
- Character sheets with class levels, validated proficiencies/loadouts, documented derived stats, HP, and combatants
- Character rules validation for levels, ability scores, proficiencies, and bonus keys
- Equipment, armor, shields, weapons, AC, and weapon attack profiles
- Equipment definition validation for impossible AC, costs, weights, damage, ranges, and metadata
- HP, healing, temporary HP, hit dice, rests, death saves, and validation for impossible HP states
- A small SRD-style creature/stat block catalog with validation for HP, AC, abilities,
  dice, movement, senses, XP, feature metadata, rechargeable action metadata, and
  immunity/resistance metadata
- Encounter helpers for challenge-rating XP, party thresholds, adjusted XP, and difficulty summaries
- SRD-style base class metadata with validation for impossible hit dice, proficiencies, and skill choices
- Condition metadata as validated mechanical tags
- Spell definitions with level, school, casting time, range, duration, components, concentration, and ritual metadata
- Spell attack bonus and spell save DC helpers
- Spell slot and pact magic state with spend and restore helpers
- Basic spell-effect helpers for spell attacks, saving throw damage, rolled healing, and conditions
- Generic limited-use resources for fixed charges, rests, proficiency-based uses, and recharge rolls
- Feature definitions and runtime feature state, with examples such as Second Wind, Rage, Sneak Attack,
  Pack Tactics, Recharge 5-6, and creature action recharge state

Good next modules:

- Effect/modifier hooks for conditions, concentration, and damage resistance
- Character advancement and multiclassing

See [ROADMAP.md](./ROADMAP.md) for phased development guidance. Future coding
agents should also read [AGENTS.md](./AGENTS.md).

## Development

```sh
python3 -m pytest
ruff check .
pyright
```

`ruff` and `pyright` are configured in `pyproject.toml`. `mypy` is intentionally
deferred until the public typing shapes settle further.

```sh
PYTHONPATH=src python3 examples/exercise_library.py
```

## Legal

See [NOTICE.md](./NOTICE.md). This package is not affiliated with or endorsed by
Wizards of the Coast.
