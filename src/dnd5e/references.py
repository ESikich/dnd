from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, TypeVar

from dnd5e.types import Ability

ABILITIES: tuple[Ability, ...] = ("str", "dex", "con", "int", "wis", "cha")
T = TypeVar("T")
LevelTableValue = bool | int | float | str


@dataclass(frozen=True)
class ReferenceItem:
    """A compact named SRD reference item with a source path."""

    id: str
    name: str
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "reference")
        if not self.name:
            raise ValueError("reference name is required")


@dataclass(frozen=True)
class AbilityScoreDefinition:
    """Ability score metadata with linked skills."""

    id: Ability
    name: str
    full_name: str
    skill_ids: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        if self.id not in ABILITIES:
            raise ValueError(f"unknown ability score: {self.id}")
        if not self.name:
            raise ValueError("ability score name is required")
        if not self.full_name:
            raise ValueError("ability score full name is required")


@dataclass(frozen=True)
class AlignmentDefinition:
    """Alignment metadata with the standard abbreviation."""

    id: str
    name: str
    abbreviation: str
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "alignment")
        if not self.name:
            raise ValueError("alignment name is required")
        if not self.abbreviation:
            raise ValueError("alignment abbreviation is required")


@dataclass(frozen=True)
class BackgroundEquipment:
    """Starting equipment entry for a background."""

    equipment_id: str
    quantity: int

    def __post_init__(self) -> None:
        _validate_id(self.equipment_id, "background equipment")
        if self.quantity < 1:
            raise ValueError("background equipment quantity must be positive")


@dataclass(frozen=True)
class BackgroundDefinition:
    """Background metadata for proficiencies, language choices, and starting gear."""

    id: str
    name: str
    starting_proficiencies: tuple[str, ...] = ()
    language_choice_count: int = 0
    language_options_url: str | None = None
    starting_equipment: tuple[BackgroundEquipment, ...] = ()
    starting_gold_quantity: int | None = None
    starting_gold_unit: str | None = None
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "background")
        if not self.name:
            raise ValueError("background name is required")
        if self.language_choice_count < 0:
            raise ValueError("background language choice count cannot be negative")
        if self.starting_gold_quantity is not None and self.starting_gold_quantity < 0:
            raise ValueError("background starting gold quantity cannot be negative")


@dataclass(frozen=True)
class EquipmentCategoryDefinition:
    """Equipment category metadata with linked equipment IDs."""

    id: str
    name: str
    equipment_ids: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "equipment category")
        if not self.name:
            raise ValueError("equipment category name is required")


@dataclass(frozen=True)
class RuleDefinition:
    """Top-level SRD rule category with linked rule sections."""

    id: str
    name: str
    subsection_ids: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "rule")
        if not self.name:
            raise ValueError("rule name is required")


@dataclass(frozen=True)
class RuleSectionDefinition:
    """SRD rule section metadata linked back to containing rule categories."""

    id: str
    name: str
    rule_ids: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "rule section")
        if not self.name:
            raise ValueError("rule section name is required")


@dataclass(frozen=True)
class SkillDefinition:
    """Skill metadata with its governing ability."""

    id: str
    name: str
    ability: Ability
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "skill")
        if not self.name:
            raise ValueError("skill name is required")
        if self.ability not in ABILITIES:
            raise ValueError(f"unknown skill ability: {self.ability}")


@dataclass(frozen=True)
class SubclassDefinition:
    """Subclass metadata linked to its parent class."""

    id: str
    name: str
    class_id: str
    subclass_flavor: str
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "subclass")
        _validate_id(self.class_id, "subclass class")
        if not self.name:
            raise ValueError("subclass name is required")
        if not self.subclass_flavor:
            raise ValueError("subclass flavor is required")


@dataclass(frozen=True)
class ClassLevelDefinition:
    """Class progression metadata for one class level."""

    id: str
    class_id: str
    level: int
    proficiency_bonus: int
    ability_score_bonuses: int
    feature_ids: tuple[str, ...] = ()
    spellcasting: dict[str, LevelTableValue] | None = None
    class_specific: dict[str, LevelTableValue] | None = None
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "class level")
        _validate_id(self.class_id, "class level class")
        _validate_level(self.level, "class level")
        if self.proficiency_bonus < 1:
            raise ValueError("class level proficiency bonus must be positive")
        if self.ability_score_bonuses < 0:
            raise ValueError("class level ability score bonuses cannot be negative")
        _validate_level_table(self.spellcasting, "class level spellcasting")
        _validate_level_table(self.class_specific, "class level class-specific")


@dataclass(frozen=True)
class SubclassLevelDefinition:
    """Subclass progression metadata for one subclass level."""

    id: str
    subclass_id: str
    class_id: str
    level: int
    feature_ids: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.id, "subclass level")
        _validate_id(self.subclass_id, "subclass level subclass")
        _validate_id(self.class_id, "subclass level class")
        _validate_level(self.level, "subclass level")


@dataclass(frozen=True)
class ReferencePack:
    """Loaded compact SRD reference metadata catalogs."""

    ability_scores: dict[str, AbilityScoreDefinition]
    alignments: dict[str, AlignmentDefinition]
    backgrounds: dict[str, BackgroundDefinition]
    damage_types: dict[str, ReferenceItem]
    equipment_categories: dict[str, EquipmentCategoryDefinition]
    magic_schools: dict[str, ReferenceItem]
    rules: dict[str, RuleDefinition]
    rule_sections: dict[str, RuleSectionDefinition]
    skills: dict[str, SkillDefinition]
    subclasses: dict[str, SubclassDefinition]
    class_levels: dict[str, ClassLevelDefinition]
    subclass_levels: dict[str, SubclassLevelDefinition]
    weapon_properties: dict[str, ReferenceItem]


def load_reference_pack(path: str | Path) -> ReferencePack:
    """Load reference definitions from a content-pack JSON file."""

    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("reference content pack must be a JSON object")
    return load_reference_pack_data(data)


def load_builtin_reference_pack() -> ReferencePack:
    """Load the packaged SRD-style reference content pack."""

    data_resource = files("dnd5e.data").joinpath("references.json")
    with data_resource.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("built-in reference content pack must be a JSON object")
    return load_reference_pack_data(data)


def load_reference_pack_data(data: Mapping[str, Any]) -> ReferencePack:
    """Validate and construct a reference pack from decoded JSON-style data."""

    _validate_pack_keys(data)
    return ReferencePack(
        ability_scores=_ability_score_catalog(data["ability_scores"]),
        alignments=_alignment_catalog(data["alignments"]),
        backgrounds=_background_catalog(data["backgrounds"]),
        damage_types=_reference_catalog(data["damage_types"], "damage_types"),
        equipment_categories=_equipment_category_catalog(data["equipment_categories"]),
        magic_schools=_reference_catalog(data["magic_schools"], "magic_schools"),
        rules=_rule_catalog(data["rules"]),
        rule_sections=_rule_section_catalog(data["rule_sections"]),
        skills=_skill_catalog(data["skills"]),
        subclasses=_subclass_catalog(data["subclasses"]),
        class_levels=_class_level_catalog(data["class_levels"]),
        subclass_levels=_subclass_level_catalog(data["subclass_levels"]),
        weapon_properties=_reference_catalog(data["weapon_properties"], "weapon_properties"),
    )


def _validate_pack_keys(data: Mapping[str, Any]) -> None:
    expected = {
        "ability_scores",
        "alignments",
        "backgrounds",
        "damage_types",
        "equipment_categories",
        "magic_schools",
        "rules",
        "rule_sections",
        "skills",
        "subclasses",
        "class_levels",
        "subclass_levels",
        "weapon_properties",
    }
    missing = expected - set(data)
    if missing:
        raise ValueError(f"reference content pack missing sections: {', '.join(sorted(missing))}")
    extra = set(data) - expected
    if extra:
        raise ValueError(f"reference content pack has unknown sections: {', '.join(sorted(extra))}")


def _ability_score_catalog(entries: Any) -> dict[str, AbilityScoreDefinition]:
    return _catalog_by_id(
        [
            AbilityScoreDefinition(
                id=_field(entry, "id", str, "ability score"),  # type: ignore[arg-type]
                name=_field(entry, "name", str, "ability score"),
                full_name=_field(entry, "full_name", str, "ability score"),
                skill_ids=_string_tuple_field(entry, "skill_ids", "ability score"),
                source_url=_optional_field(entry, "source_url", str, "ability score"),
            )
            for entry in _entries(entries, "ability_scores", {"id", "name", "full_name", "skill_ids", "source_url"})
        ],
        "ability score",
    )


def _alignment_catalog(entries: Any) -> dict[str, AlignmentDefinition]:
    return _catalog_by_id(
        [
            AlignmentDefinition(
                id=_field(entry, "id", str, "alignment"),
                name=_field(entry, "name", str, "alignment"),
                abbreviation=_field(entry, "abbreviation", str, "alignment"),
                source_url=_optional_field(entry, "source_url", str, "alignment"),
            )
            for entry in _entries(entries, "alignments", {"id", "name", "abbreviation", "source_url"})
        ],
        "alignment",
    )


def _background_catalog(entries: Any) -> dict[str, BackgroundDefinition]:
    return _catalog_by_id(
        [
            BackgroundDefinition(
                id=_field(entry, "id", str, "background"),
                name=_field(entry, "name", str, "background"),
                starting_proficiencies=_string_tuple_field(entry, "starting_proficiencies", "background"),
                language_choice_count=_field(entry, "language_choice_count", int, "background"),
                language_options_url=_optional_field(entry, "language_options_url", str, "background"),
                starting_equipment=tuple(_background_equipment_entries(entry)),
                starting_gold_quantity=_optional_field(entry, "starting_gold_quantity", int, "background"),
                starting_gold_unit=_optional_field(entry, "starting_gold_unit", str, "background"),
                source_url=_optional_field(entry, "source_url", str, "background"),
            )
            for entry in _entries(
                entries,
                "backgrounds",
                {
                    "id",
                    "name",
                    "starting_proficiencies",
                    "language_choice_count",
                    "language_options_url",
                    "starting_equipment",
                    "starting_gold_quantity",
                    "starting_gold_unit",
                    "source_url",
                },
            )
        ],
        "background",
    )


def _reference_catalog(entries: Any, section: str) -> dict[str, ReferenceItem]:
    return _catalog_by_id(
        [
            ReferenceItem(
                id=_field(entry, "id", str, "reference"),
                name=_field(entry, "name", str, "reference"),
                source_url=_optional_field(entry, "source_url", str, "reference"),
            )
            for entry in _entries(entries, section, {"id", "name", "source_url"})
        ],
        section,
    )


def _equipment_category_catalog(entries: Any) -> dict[str, EquipmentCategoryDefinition]:
    return _catalog_by_id(
        [
            EquipmentCategoryDefinition(
                id=_field(entry, "id", str, "equipment category"),
                name=_field(entry, "name", str, "equipment category"),
                equipment_ids=_string_tuple_field(entry, "equipment_ids", "equipment category"),
                source_url=_optional_field(entry, "source_url", str, "equipment category"),
            )
            for entry in _entries(entries, "equipment_categories", {"id", "name", "equipment_ids", "source_url"})
        ],
        "equipment category",
    )


def _rule_catalog(entries: Any) -> dict[str, RuleDefinition]:
    return _catalog_by_id(
        [
            RuleDefinition(
                id=_field(entry, "id", str, "rule"),
                name=_field(entry, "name", str, "rule"),
                subsection_ids=_string_tuple_field(entry, "subsection_ids", "rule"),
                source_url=_optional_field(entry, "source_url", str, "rule"),
            )
            for entry in _entries(entries, "rules", {"id", "name", "subsection_ids", "source_url"})
        ],
        "rule",
    )


def _rule_section_catalog(entries: Any) -> dict[str, RuleSectionDefinition]:
    return _catalog_by_id(
        [
            RuleSectionDefinition(
                id=_field(entry, "id", str, "rule section"),
                name=_field(entry, "name", str, "rule section"),
                rule_ids=_string_tuple_field(entry, "rule_ids", "rule section"),
                source_url=_optional_field(entry, "source_url", str, "rule section"),
            )
            for entry in _entries(entries, "rule_sections", {"id", "name", "rule_ids", "source_url"})
        ],
        "rule section",
    )


def _skill_catalog(entries: Any) -> dict[str, SkillDefinition]:
    return _catalog_by_id(
        [
            SkillDefinition(
                id=_field(entry, "id", str, "skill"),
                name=_field(entry, "name", str, "skill"),
                ability=_field(entry, "ability", str, "skill"),  # type: ignore[arg-type]
                source_url=_optional_field(entry, "source_url", str, "skill"),
            )
            for entry in _entries(entries, "skills", {"id", "name", "ability", "source_url"})
        ],
        "skill",
    )


def _subclass_catalog(entries: Any) -> dict[str, SubclassDefinition]:
    return _catalog_by_id(
        [
            SubclassDefinition(
                id=_field(entry, "id", str, "subclass"),
                name=_field(entry, "name", str, "subclass"),
                class_id=_field(entry, "class_id", str, "subclass"),
                subclass_flavor=_field(entry, "subclass_flavor", str, "subclass"),
                source_url=_optional_field(entry, "source_url", str, "subclass"),
            )
            for entry in _entries(entries, "subclasses", {"id", "name", "class_id", "subclass_flavor", "source_url"})
        ],
        "subclass",
    )


def _class_level_catalog(entries: Any) -> dict[str, ClassLevelDefinition]:
    return _catalog_by_id(
        [
            ClassLevelDefinition(
                id=_field(entry, "id", str, "class level"),
                class_id=_field(entry, "class_id", str, "class level"),
                level=_field(entry, "level", int, "class level"),
                proficiency_bonus=_field(entry, "proficiency_bonus", int, "class level"),
                ability_score_bonuses=_field(entry, "ability_score_bonuses", int, "class level"),
                feature_ids=_string_tuple_field(entry, "feature_ids", "class level"),
                spellcasting=_optional_level_table_field(entry, "spellcasting", "class level"),
                class_specific=_optional_level_table_field(entry, "class_specific", "class level"),
                source_url=_optional_field(entry, "source_url", str, "class level"),
            )
            for entry in _entries(
                entries,
                "class_levels",
                {
                    "id",
                    "class_id",
                    "level",
                    "proficiency_bonus",
                    "ability_score_bonuses",
                    "feature_ids",
                    "spellcasting",
                    "class_specific",
                    "source_url",
                },
            )
        ],
        "class level",
    )


def _subclass_level_catalog(entries: Any) -> dict[str, SubclassLevelDefinition]:
    return _catalog_by_id(
        [
            SubclassLevelDefinition(
                id=_field(entry, "id", str, "subclass level"),
                subclass_id=_field(entry, "subclass_id", str, "subclass level"),
                class_id=_field(entry, "class_id", str, "subclass level"),
                level=_field(entry, "level", int, "subclass level"),
                feature_ids=_string_tuple_field(entry, "feature_ids", "subclass level"),
                source_url=_optional_field(entry, "source_url", str, "subclass level"),
            )
            for entry in _entries(
                entries,
                "subclass_levels",
                {"id", "subclass_id", "class_id", "level", "feature_ids", "source_url"},
            )
        ],
        "subclass level",
    )


def _background_equipment_entries(entry: Mapping[str, Any]) -> tuple[BackgroundEquipment, ...]:
    return tuple(
        BackgroundEquipment(
            equipment_id=_field(item, "equipment_id", str, "background equipment"),
            quantity=_field(item, "quantity", int, "background equipment"),
        )
        for item in _nested_entries(entry, "starting_equipment", "background", {"equipment_id", "quantity"})
    )


def _entries(entries: Any, section: str, expected_fields: set[str]) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(entries, list):
        raise ValueError(f"reference content section {section} must be a list")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError(f"reference content section {section} entries must be objects")
        extra = set(entry) - expected_fields
        if extra:
            raise ValueError(f"{section} entry has unknown fields: {', '.join(sorted(extra))}")
    return tuple(entries)


def _nested_entries(
    entry: Mapping[str, Any],
    name: str,
    section: str,
    expected_fields: set[str],
) -> tuple[Mapping[str, Any], ...]:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, list):
        raise ValueError(f"{section}.{name} must be a list")
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"{section}.{name} entries must be objects")
        extra = set(item) - expected_fields
        if extra:
            raise ValueError(f"{section}.{name} entry has unknown fields: {', '.join(sorted(extra))}")
    return tuple(value)


def _catalog_by_id(entries: list[T], section: str) -> dict[str, T]:
    catalog: dict[str, T] = {}
    for entry in entries:
        id_ = getattr(entry, "id")
        if id_ in catalog:
            raise ValueError(f"duplicate {section} id: {id_}")
        catalog[id_] = entry
    return catalog


def _field(entry: Mapping[str, Any], name: str, expected_type: type[T], section: str) -> T:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__}")
    return value


def _optional_field(
    entry: Mapping[str, Any],
    name: str,
    expected_type: type[T],
    section: str,
) -> T | None:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if value is None:
        return None
    if not isinstance(value, expected_type):
        raise ValueError(f"{section}.{name} must be {expected_type.__name__} or null")
    return value


def _optional_level_table_field(
    entry: Mapping[str, Any],
    name: str,
    section: str,
) -> dict[str, LevelTableValue] | None:
    value = _optional_field(entry, name, dict, section)
    if value is None:
        return None
    _validate_level_table(value, f"{section}.{name}")
    return value


def _string_tuple_field(entry: Mapping[str, Any], name: str, section: str) -> tuple[str, ...]:
    if name not in entry:
        raise ValueError(f"{section} entry missing field: {name}")
    value = entry[name]
    if not isinstance(value, list):
        raise ValueError(f"{section}.{name} must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{section}.{name} entries must be strings")
    return tuple(value)


def _validate_id(value: str, section: str) -> None:
    if not value:
        raise ValueError(f"{section} id is required")


def _validate_level(value: int, section: str) -> None:
    if not 1 <= value <= 20:
        raise ValueError(f"{section} must be from 1 to 20")


def _validate_level_table(values: Mapping[str, Any] | None, section: str) -> None:
    if values is None:
        return
    for key, value in values.items():
        if not isinstance(key, str):
            raise ValueError(f"{section} keys must be strings")
        if not isinstance(value, bool | int | float | str):
            raise ValueError(f"{section}.{key} must be a primitive table value")


_BUILTIN_REFERENCES = load_builtin_reference_pack()
ABILITY_SCORES: dict[str, AbilityScoreDefinition] = _BUILTIN_REFERENCES.ability_scores
ALIGNMENTS: dict[str, AlignmentDefinition] = _BUILTIN_REFERENCES.alignments
BACKGROUNDS: dict[str, BackgroundDefinition] = _BUILTIN_REFERENCES.backgrounds
DAMAGE_TYPE_REFERENCES: dict[str, ReferenceItem] = _BUILTIN_REFERENCES.damage_types
EQUIPMENT_CATEGORIES: dict[str, EquipmentCategoryDefinition] = _BUILTIN_REFERENCES.equipment_categories
MAGIC_SCHOOLS: dict[str, ReferenceItem] = _BUILTIN_REFERENCES.magic_schools
RULES: dict[str, RuleDefinition] = _BUILTIN_REFERENCES.rules
RULE_SECTIONS: dict[str, RuleSectionDefinition] = _BUILTIN_REFERENCES.rule_sections
SKILLS: dict[str, SkillDefinition] = _BUILTIN_REFERENCES.skills
SUBCLASSES: dict[str, SubclassDefinition] = _BUILTIN_REFERENCES.subclasses
CLASS_LEVELS: dict[str, ClassLevelDefinition] = _BUILTIN_REFERENCES.class_levels
SUBCLASS_LEVELS: dict[str, SubclassLevelDefinition] = _BUILTIN_REFERENCES.subclass_levels
WEAPON_PROPERTY_REFERENCES: dict[str, ReferenceItem] = _BUILTIN_REFERENCES.weapon_properties
