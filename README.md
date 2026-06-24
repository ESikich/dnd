# D&D 5e Rules Library

A Python library for formalizing 5E-compatible rules, mechanics, combat,
character math, classes, creatures, equipment, HP, and conditions.

The first version is mechanics-first: it gives you typed primitives and rule
helpers without copying long-form rule text.

## Install

```sh
python -m pip install -e .
```

## Use

```py
from dnd5e import (
    CREATURES,
    CharacterClassLevel,
    CharacterLoadout,
    CharacterSheet,
    HitPointState,
    SRD_CLASSES,
    ability_modifier,
    attack_roll,
    character_sheet_armor_class,
    character_sheet_combatant,
    character_sheet_weapon_profile,
    combatant_by_id,
    create_combat,
    create_combatant,
    create_creature_instance,
    d20_check,
    creature_runtime_combatant,
    resolve_attack_action,
    roll_dice,
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

print(ability_modifier(16))  # 3
print(athletics.total)  # 17
print(combat.current.name)  # "Fighter"
print(result.attack.outcome)  # "hit"
print(combatant_by_id(result.state, "goblin").hit_points.current)  # 3
print(kara_ac.total)  # 18
print(kara_weapon.attack_bonus)  # 6
print(kara_combatant.hit_points.maximum)  # 44
print(goblin_combatant.armor_class)  # 15
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
- Basic creature/stat block definitions with validation for HP, AC, abilities, dice, movement, senses, and XP
- SRD-style base class metadata with validation for impossible hit dice, proficiencies, and skill choices
- Condition metadata as validated mechanical tags

Good next modules:

- Encounter difficulty
- Spell definitions and spellcasting rules
- Resources and feature recharge
- Character advancement and multiclassing

See [ROADMAP.md](./ROADMAP.md) for phased development guidance. Future coding
agents should also read [AGENTS.md](./AGENTS.md).

## Development

```sh
python3 -m pytest
python3 -m ruff check .
```

`ruff` is configured in `pyproject.toml`; install it in your environment before
running the lint command. `mypy` is intentionally deferred until the public
typing shapes settle further.

```sh
PYTHONPATH=src python3 examples/exercise_library.py
```

## Legal

See [NOTICE.md](./NOTICE.md). This package is not affiliated with or endorsed by
Wizards of the Coast.
