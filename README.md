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
    HitPointState,
    SRD_CLASSES,
    ability_modifier,
    combatant_by_id,
    create_combat,
    create_combatant,
    d20_check,
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
- Combat runtime state with AC, HP, conditions, attack resolution, and healing
- Equipment, armor, shields, weapons, AC, and weapon attack profiles
- HP, healing, temporary HP, hit dice, rests, and death saves
- Basic creature/stat block definitions
- SRD-style base class metadata
- Condition metadata as mechanical tags

Good next modules:

- Character sheet model
- Spell definitions and spellcasting rules
- Encounter difficulty
- Resources and feature recharge
- Character advancement and multiclassing

See [ROADMAP.md](./ROADMAP.md) for phased development guidance. Future coding
agents should also read [AGENTS.md](./AGENTS.md).

## Test

```sh
python -m pytest
```

## Demo

```sh
PYTHONPATH=src python examples/exercise_library.py
```

## Legal

See [NOTICE.md](./NOTICE.md). This package is not affiliated with or endorsed by
Wizards of the Coast.
