from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from dnd5e.ancestries import AncestryPack, load_ancestry_pack_data, load_builtin_ancestry_pack
from dnd5e.classes import ClassPack, load_builtin_class_pack, load_class_pack_data
from dnd5e.conditions import ConditionPack, load_builtin_condition_pack, load_condition_pack_data
from dnd5e.creatures import CreaturePack, load_builtin_creature_pack, load_creature_pack_data
from dnd5e.encounters import (
    EncounterRulesPack,
    load_builtin_encounter_rules_pack,
    load_encounter_rules_pack_data,
)
from dnd5e.equipment import EquipmentPack, load_builtin_equipment_pack, load_equipment_pack_data
from dnd5e.resources import FeaturePack, load_builtin_feature_pack, load_feature_pack_data
from dnd5e.references import ReferencePack, load_builtin_reference_pack, load_reference_pack_data
from dnd5e.spells import SpellPack, load_builtin_spell_pack, load_spell_pack_data

T = TypeVar("T")


@dataclass(frozen=True)
class ContentPack:
    """A bundled content pack made from any supported domain content sections."""

    equipment: EquipmentPack | None = None
    classes: ClassPack | None = None
    spells: SpellPack | None = None
    features: FeaturePack | None = None
    creatures: CreaturePack | None = None
    conditions: ConditionPack | None = None
    encounter_rules: EncounterRulesPack | None = None
    ancestries: AncestryPack | None = None
    references: ReferencePack | None = None

    def __post_init__(self) -> None:
        if not any(
            (
                self.equipment,
                self.classes,
                self.spells,
                self.features,
                self.creatures,
                self.conditions,
                self.encounter_rules,
                self.ancestries,
                self.references,
            )
        ):
            raise ValueError("content pack requires at least one content section")


CONTENT_PACK_SECTIONS: tuple[str, ...] = (
    "equipment",
    "classes",
    "spells",
    "features",
    "creatures",
    "conditions",
    "encounter_rules",
    "ancestries",
    "references",
)


def load_content_pack(path: str | Path) -> ContentPack:
    """Load a bundled user content-pack JSON file with any supported sections."""

    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("content pack must be a JSON object")
    return load_content_pack_data(data)


def load_builtin_content_pack() -> ContentPack:
    """Load all packaged SRD-style content packs as one bundle."""

    return ContentPack(
        equipment=load_builtin_equipment_pack(),
        classes=load_builtin_class_pack(),
        spells=load_builtin_spell_pack(),
        features=load_builtin_feature_pack(),
        creatures=load_builtin_creature_pack(),
        conditions=load_builtin_condition_pack(),
        encounter_rules=load_builtin_encounter_rules_pack(),
        ancestries=load_builtin_ancestry_pack(),
        references=load_builtin_reference_pack(),
    )


def load_content_pack_data(data: Mapping[str, Any]) -> ContentPack:
    """Validate and construct a bundled content pack from decoded JSON-style data."""

    _validate_pack_keys(data)
    return ContentPack(
        equipment=_load_optional_section(data, "equipment", load_equipment_pack_data),
        classes=_load_optional_section(data, "classes", load_class_pack_data),
        spells=_load_optional_section(data, "spells", load_spell_pack_data),
        features=_load_optional_section(data, "features", load_feature_pack_data),
        creatures=_load_optional_section(data, "creatures", load_creature_pack_data),
        conditions=_load_optional_section(data, "conditions", load_condition_pack_data),
        encounter_rules=_load_optional_section(
            data,
            "encounter_rules",
            load_encounter_rules_pack_data,
        ),
        ancestries=_load_optional_section(data, "ancestries", load_ancestry_pack_data),
        references=_load_optional_section(data, "references", load_reference_pack_data),
    )


def _validate_pack_keys(data: Mapping[str, Any]) -> None:
    if not data:
        raise ValueError("content pack requires at least one content section")
    extra = set(data) - set(CONTENT_PACK_SECTIONS)
    if extra:
        raise ValueError(f"content pack has unknown sections: {', '.join(sorted(extra))}")


def _load_optional_section(
    data: Mapping[str, Any],
    section: str,
    loader: Callable[[Mapping[str, Any]], T],
) -> T | None:
    if section not in data:
        return None
    value = data[section]
    if not isinstance(value, Mapping):
        raise ValueError(f"content pack section {section} must be a JSON object")
    return loader(value)
