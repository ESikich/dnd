from __future__ import annotations

from typing import Literal

Ability = Literal["str", "dex", "con", "int", "wis", "cha"]

Skill = Literal[
    "acrobatics",
    "animal_handling",
    "arcana",
    "athletics",
    "deception",
    "history",
    "insight",
    "intimidation",
    "investigation",
    "medicine",
    "nature",
    "perception",
    "performance",
    "persuasion",
    "religion",
    "sleight_of_hand",
    "stealth",
    "survival",
]

AdvantageState = Literal["normal", "advantage", "disadvantage"]
ProficiencyLevel = Literal["none", "half", "proficient", "expertise"]

DamageType = Literal[
    "acid",
    "bludgeoning",
    "cold",
    "fire",
    "force",
    "lightning",
    "necrotic",
    "piercing",
    "poison",
    "psychic",
    "radiant",
    "slashing",
    "thunder",
]

ArmorCategory = Literal["light", "medium", "heavy"]
ArmorTraining = Literal["light", "medium", "heavy", "shield"]
WeaponCategory = Literal["simple", "martial"]
WeaponRangeType = Literal["melee", "ranged"]
WeaponProperty = Literal[
    "ammunition",
    "finesse",
    "heavy",
    "light",
    "loading",
    "range",
    "reach",
    "special",
    "thrown",
    "two_handed",
    "versatile",
]
WeaponTraining = Literal["simple", "martial"]

CharacterClassName = Literal[
    "barbarian",
    "bard",
    "cleric",
    "druid",
    "fighter",
    "monk",
    "paladin",
    "ranger",
    "rogue",
    "sorcerer",
    "warlock",
    "wizard",
]

CreatureSize = Literal["tiny", "small", "medium", "large", "huge", "gargantuan"]
CreatureType = Literal[
    "aberration",
    "beast",
    "celestial",
    "construct",
    "dragon",
    "elemental",
    "fey",
    "fiend",
    "giant",
    "humanoid",
    "monstrosity",
    "ooze",
    "plant",
    "undead",
]

AttackOutcome = Literal["critical-miss", "miss", "hit", "critical-hit"]

ConditionName = Literal[
    "blinded",
    "charmed",
    "deafened",
    "frightened",
    "grappled",
    "incapacitated",
    "invisible",
    "paralyzed",
    "petrified",
    "poisoned",
    "prone",
    "restrained",
    "stunned",
    "unconscious",
]

ConditionTag = Literal[
    "cannot_move",
    "cannot_act",
    "cannot_see",
    "cannot_hear",
    "attack_rolls_affected",
    "ability_checks_affected",
    "saving_throws_affected",
    "speed_zero",
    "melee_attackers_affected",
    "auto_fail_strength_dexterity_saves",
    "critical_hits_from_nearby_attackers",
]

SpellSchool = Literal[
    "abjuration",
    "conjuration",
    "divination",
    "enchantment",
    "evocation",
    "illusion",
    "necromancy",
    "transmutation",
]

SpellComponent = Literal["verbal", "somatic", "material"]
