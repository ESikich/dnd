from __future__ import annotations

from dataclasses import dataclass

from dnd5e.types import Ability, ArmorTraining, CharacterClassName, Skill, WeaponTraining


@dataclass(frozen=True)
class ClassDefinition:
    name: CharacterClassName
    hit_die: int
    primary_abilities: tuple[Ability, ...]
    saving_throws: tuple[Ability, ...]
    armor_training: tuple[ArmorTraining, ...]
    weapon_training: tuple[WeaponTraining, ...]
    skill_choices: tuple[Skill, ...]
    skill_choice_count: int


SRD_CLASSES: dict[CharacterClassName, ClassDefinition] = {
    "barbarian": ClassDefinition(
        "barbarian",
        12,
        ("str",),
        ("str", "con"),
        ("light", "medium", "shield"),
        ("simple", "martial"),
        ("animal_handling", "athletics", "intimidation", "nature", "perception", "survival"),
        2,
    ),
    "bard": ClassDefinition(
        "bard",
        8,
        ("cha",),
        ("dex", "cha"),
        ("light",),
        ("simple",),
        (
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
        ),
        3,
    ),
    "cleric": ClassDefinition(
        "cleric",
        8,
        ("wis",),
        ("wis", "cha"),
        ("light", "medium", "shield"),
        ("simple",),
        ("history", "insight", "medicine", "persuasion", "religion"),
        2,
    ),
    "druid": ClassDefinition(
        "druid",
        8,
        ("wis",),
        ("int", "wis"),
        ("light", "medium", "shield"),
        ("simple",),
        ("arcana", "animal_handling", "insight", "medicine", "nature", "perception", "religion", "survival"),
        2,
    ),
    "fighter": ClassDefinition(
        "fighter",
        10,
        ("str", "dex"),
        ("str", "con"),
        ("light", "medium", "heavy", "shield"),
        ("simple", "martial"),
        ("acrobatics", "animal_handling", "athletics", "history", "insight", "intimidation", "perception", "survival"),
        2,
    ),
    "monk": ClassDefinition(
        "monk",
        8,
        ("dex", "wis"),
        ("str", "dex"),
        (),
        ("simple",),
        ("acrobatics", "athletics", "history", "insight", "religion", "stealth"),
        2,
    ),
    "paladin": ClassDefinition(
        "paladin",
        10,
        ("str", "cha"),
        ("wis", "cha"),
        ("light", "medium", "heavy", "shield"),
        ("simple", "martial"),
        ("athletics", "insight", "intimidation", "medicine", "persuasion", "religion"),
        2,
    ),
    "ranger": ClassDefinition(
        "ranger",
        10,
        ("dex", "wis"),
        ("str", "dex"),
        ("light", "medium", "shield"),
        ("simple", "martial"),
        ("animal_handling", "athletics", "insight", "investigation", "nature", "perception", "stealth", "survival"),
        3,
    ),
    "rogue": ClassDefinition(
        "rogue",
        8,
        ("dex",),
        ("dex", "int"),
        ("light",),
        ("simple",),
        (
            "acrobatics",
            "athletics",
            "deception",
            "insight",
            "intimidation",
            "investigation",
            "perception",
            "performance",
            "persuasion",
            "sleight_of_hand",
            "stealth",
        ),
        4,
    ),
    "sorcerer": ClassDefinition(
        "sorcerer",
        6,
        ("cha",),
        ("con", "cha"),
        (),
        ("simple",),
        ("arcana", "deception", "insight", "intimidation", "persuasion", "religion"),
        2,
    ),
    "warlock": ClassDefinition(
        "warlock",
        8,
        ("cha",),
        ("wis", "cha"),
        ("light",),
        ("simple",),
        ("arcana", "deception", "history", "intimidation", "investigation", "nature", "religion"),
        2,
    ),
    "wizard": ClassDefinition(
        "wizard",
        6,
        ("int",),
        ("int", "wis"),
        (),
        ("simple",),
        ("arcana", "history", "insight", "investigation", "medicine", "religion"),
        2,
    ),
}
