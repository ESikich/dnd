from __future__ import annotations

from dataclasses import dataclass, field

from dnd5e.references import (
    CLASS_LEVELS,
    SUBCLASS_LEVELS,
    ClassLevelDefinition,
    LevelTableValue,
    SubclassLevelDefinition,
)
from dnd5e.resources import FEATURES, FeatureDefinition
from dnd5e.sheets import CharacterSheet


@dataclass(frozen=True)
class CharacterClassProgression:
    """Class progression entries, features, and table values granted to a sheet."""

    class_levels: tuple[ClassLevelDefinition, ...]
    subclass_levels: tuple[SubclassLevelDefinition, ...] = ()
    features: tuple[FeatureDefinition, ...] = ()
    spellcasting: dict[str, LevelTableValue] | None = None
    class_specific: dict[str, LevelTableValue] = field(default_factory=dict)
    ability_score_bonuses: int = 0


@dataclass(frozen=True)
class CharacterSpellcastingProgression:
    """Spellcasting table values projected into cantrips and spell slot counts."""

    cantrips_known: int | None = None
    spells_known: int | None = None
    spell_slots: dict[int, int] = field(default_factory=dict)
    raw: dict[str, LevelTableValue] = field(default_factory=dict)


def character_sheet_class_progression(
    sheet: CharacterSheet,
    *,
    subclasses: dict[str, str] | None = None,
) -> CharacterClassProgression:
    """Return class and optional subclass progression granted by a character sheet."""

    class_levels: list[ClassLevelDefinition] = []
    subclass_levels: list[SubclassLevelDefinition] = []
    feature_ids: list[str] = []
    class_specific: dict[str, LevelTableValue] = {}
    spellcasting: dict[str, LevelTableValue] | None = None
    ability_score_bonuses = 0

    for class_entry in sheet.classes:
        for level in range(1, class_entry.level + 1):
            class_level = _class_level(class_entry.name, level)
            class_levels.append(class_level)
            feature_ids.extend(class_level.feature_ids)
            ability_score_bonuses += class_level.ability_score_bonuses
            if class_level.class_specific is not None:
                class_specific.update(class_level.class_specific)
            if class_level.spellcasting is not None:
                spellcasting = dict(class_level.spellcasting)

            subclass_id = subclasses.get(class_entry.name) if subclasses else None
            if subclass_id is not None:
                subclass_level = _subclass_level(subclass_id, class_entry.name, level)
                if subclass_level is not None:
                    subclass_levels.append(subclass_level)
                    feature_ids.extend(subclass_level.feature_ids)

    return CharacterClassProgression(
        class_levels=tuple(class_levels),
        subclass_levels=tuple(subclass_levels),
        features=_features(feature_ids),
        spellcasting=spellcasting,
        class_specific=class_specific,
        ability_score_bonuses=ability_score_bonuses,
    )


def character_sheet_class_features(
    sheet: CharacterSheet,
    *,
    subclasses: dict[str, str] | None = None,
) -> tuple[FeatureDefinition, ...]:
    """Return feature definitions granted by class and optional subclass levels."""

    return character_sheet_class_progression(sheet, subclasses=subclasses).features


def character_sheet_spellcasting_progression(
    sheet: CharacterSheet,
) -> CharacterSpellcastingProgression | None:
    """Return spellcasting table values for a single-class sheet, when present."""

    progression = character_sheet_class_progression(sheet)
    if progression.spellcasting is None:
        return None

    return CharacterSpellcastingProgression(
        cantrips_known=_optional_int(progression.spellcasting.get("cantrips_known")),
        spells_known=_optional_int(progression.spellcasting.get("spells_known")),
        spell_slots={
            level: value
            for level in range(1, 10)
            if (value := _optional_int(progression.spellcasting.get(f"spell_slots_level_{level}")))
            is not None
            and value > 0
        },
        raw=dict(progression.spellcasting),
    )


def _class_level(class_id: str, level: int) -> ClassLevelDefinition:
    key = f"{class_id}-{level}"
    try:
        return CLASS_LEVELS[key]
    except KeyError as error:
        raise ValueError(f"unknown class level: {key}") from error


def _subclass_level(
    subclass_id: str,
    class_id: str,
    level: int,
) -> SubclassLevelDefinition | None:
    key = f"{subclass_id}-{level}"
    if key not in SUBCLASS_LEVELS:
        return None
    subclass_level = SUBCLASS_LEVELS[key]
    if subclass_level.class_id != class_id:
        raise ValueError("subclass does not belong to class")
    return subclass_level


def _features(feature_ids: list[str]) -> tuple[FeatureDefinition, ...]:
    return tuple(FEATURES[_feature_key(feature_id)] for feature_id in dict.fromkeys(feature_ids))


def _feature_key(feature_id: str) -> str:
    return feature_id.replace("-", "_")


def _optional_int(value: LevelTableValue | None) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
