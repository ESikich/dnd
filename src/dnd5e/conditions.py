from __future__ import annotations

from dataclasses import dataclass

from dnd5e.types import ConditionName, ConditionTag


@dataclass(frozen=True)
class ConditionDefinition:
    name: ConditionName
    tags: tuple[ConditionTag, ...]


CONDITIONS: dict[ConditionName, ConditionDefinition] = {
    "blinded": ConditionDefinition("blinded", ("cannot_see", "attack_rolls_affected")),
    "charmed": ConditionDefinition("charmed", ("ability_checks_affected",)),
    "deafened": ConditionDefinition("deafened", ("cannot_hear",)),
    "frightened": ConditionDefinition("frightened", ("attack_rolls_affected", "ability_checks_affected")),
    "grappled": ConditionDefinition("grappled", ("speed_zero",)),
    "incapacitated": ConditionDefinition("incapacitated", ("cannot_act",)),
    "invisible": ConditionDefinition("invisible", ("attack_rolls_affected",)),
    "paralyzed": ConditionDefinition(
        "paralyzed",
        (
            "cannot_act",
            "cannot_move",
            "auto_fail_strength_dexterity_saves",
            "attack_rolls_affected",
            "critical_hits_from_nearby_attackers",
        ),
    ),
    "petrified": ConditionDefinition(
        "petrified",
        ("cannot_act", "cannot_move", "auto_fail_strength_dexterity_saves", "attack_rolls_affected"),
    ),
    "poisoned": ConditionDefinition("poisoned", ("attack_rolls_affected", "ability_checks_affected")),
    "prone": ConditionDefinition("prone", ("attack_rolls_affected", "melee_attackers_affected")),
    "restrained": ConditionDefinition("restrained", ("speed_zero", "attack_rolls_affected", "saving_throws_affected")),
    "stunned": ConditionDefinition(
        "stunned",
        ("cannot_act", "cannot_move", "auto_fail_strength_dexterity_saves", "attack_rolls_affected"),
    ),
    "unconscious": ConditionDefinition(
        "unconscious",
        (
            "cannot_act",
            "cannot_move",
            "attack_rolls_affected",
            "auto_fail_strength_dexterity_saves",
            "critical_hits_from_nearby_attackers",
        ),
    ),
}
