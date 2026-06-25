from pathlib import Path

import pytest

from dnd5e import (
    ABILITY_SCORES,
    ALIGNMENTS,
    BACKGROUNDS,
    CLASS_LEVELS,
    DAMAGE_TYPE_REFERENCES,
    EQUIPMENT_CATEGORIES,
    MAGIC_SCHOOLS,
    RULES,
    RULE_SECTIONS,
    SKILLS,
    SUBCLASSES,
    SUBCLASS_LEVELS,
    WEAPON_PROPERTY_REFERENCES,
    AbilityScoreDefinition,
    AlignmentDefinition,
    BackgroundDefinition,
    BackgroundEquipment,
    ClassLevelDefinition,
    EquipmentCategoryDefinition,
    ReferenceItem,
    ReferencePack,
    RuleDefinition,
    RuleSectionDefinition,
    SkillDefinition,
    SubclassDefinition,
    SubclassLevelDefinition,
    load_builtin_reference_pack,
    load_reference_pack,
    load_reference_pack_data,
)


def _reference_pack_data(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "ability_scores": [
            {
                "id": "str",
                "name": "STR",
                "full_name": "Strength",
                "skill_ids": ["athletics"],
                "source_url": None,
            }
        ],
        "alignments": [
            {"id": "neutral", "name": "Neutral", "abbreviation": "N", "source_url": None}
        ],
        "backgrounds": [
            {
                "id": "wanderer",
                "name": "Wanderer",
                "starting_proficiencies": ["skill-survival"],
                "language_choice_count": 1,
                "language_options_url": "/api/2014/languages",
                "starting_equipment": [{"equipment_id": "staff", "quantity": 1}],
                "starting_gold_quantity": 10,
                "starting_gold_unit": "gp",
                "source_url": None,
            }
        ],
        "damage_types": [{"id": "fire", "name": "Fire", "source_url": None}],
        "equipment_categories": [
            {
                "id": "weapons",
                "name": "Weapons",
                "equipment_ids": ["longsword"],
                "source_url": None,
            }
        ],
        "magic_schools": [{"id": "evocation", "name": "Evocation", "source_url": None}],
        "rules": [
            {
                "id": "combat",
                "name": "Combat",
                "subsection_ids": ["actions-in-combat"],
                "source_url": None,
            }
        ],
        "rule_sections": [
            {
                "id": "actions-in-combat",
                "name": "Actions in Combat",
                "rule_ids": ["combat"],
                "source_url": None,
            }
        ],
        "skills": [
            {"id": "athletics", "name": "Athletics", "ability": "str", "source_url": None}
        ],
        "subclasses": [
            {
                "id": "champion",
                "name": "Champion",
                "class_id": "fighter",
                "subclass_flavor": "Martial Archetype",
                "source_url": None,
            }
        ],
        "class_levels": [
            {
                "id": "fighter-1",
                "class_id": "fighter",
                "level": 1,
                "proficiency_bonus": 2,
                "ability_score_bonuses": 0,
                "feature_ids": ["second-wind"],
                "spellcasting": None,
                "class_specific": {"action_surges": 0},
                "source_url": None,
            }
        ],
        "subclass_levels": [
            {
                "id": "champion-3",
                "subclass_id": "champion",
                "class_id": "fighter",
                "level": 3,
                "feature_ids": ["improved-critical"],
                "source_url": None,
            }
        ],
        "weapon_properties": [{"id": "finesse", "name": "Finesse", "source_url": None}],
    }
    values.update(overrides)
    return values


def test_public_reference_imports_and_docstrings() -> None:
    assert isinstance(ABILITY_SCORES["str"], AbilityScoreDefinition)
    assert isinstance(ALIGNMENTS["lawful-good"], AlignmentDefinition)
    assert isinstance(BACKGROUNDS["acolyte"], BackgroundDefinition)
    assert isinstance(DAMAGE_TYPE_REFERENCES["fire"], ReferenceItem)
    assert isinstance(EQUIPMENT_CATEGORIES["weapon"], EquipmentCategoryDefinition)
    assert isinstance(MAGIC_SCHOOLS["evocation"], ReferenceItem)
    assert isinstance(RULES["combat"], RuleDefinition)
    assert isinstance(RULE_SECTIONS["actions-in-combat"], RuleSectionDefinition)
    assert isinstance(SKILLS["athletics"], SkillDefinition)
    assert isinstance(SUBCLASSES["champion"], SubclassDefinition)
    assert isinstance(CLASS_LEVELS["fighter-1"], ClassLevelDefinition)
    assert isinstance(SUBCLASS_LEVELS["champion-3"], SubclassLevelDefinition)
    assert isinstance(WEAPON_PROPERTY_REFERENCES["finesse"], ReferenceItem)
    assert isinstance(load_builtin_reference_pack(), ReferencePack)


def test_builtin_reference_pack_loads_remaining_srd_catalogs() -> None:
    pack = load_builtin_reference_pack()

    assert pack.ability_scores == ABILITY_SCORES
    assert len(pack.ability_scores) == 6
    assert len(pack.alignments) == 9
    assert len(pack.backgrounds) == 1
    assert len(pack.damage_types) == 13
    assert len(pack.equipment_categories) == 39
    assert len(pack.magic_schools) == 8
    assert len(pack.rules) == 6
    assert len(pack.rule_sections) == 33
    assert len(pack.skills) == 18
    assert len(pack.subclasses) == 12
    assert len(pack.class_levels) == 240
    assert len(pack.subclass_levels) == 50
    assert len(pack.weapon_properties) == 11
    assert pack.ability_scores["str"].skill_ids == ("athletics",)
    assert pack.backgrounds["acolyte"].starting_proficiencies == (
        "skill-insight",
        "skill-religion",
    )
    assert pack.backgrounds["acolyte"].language_choice_count == 2
    assert pack.equipment_categories["weapon"].equipment_ids
    assert "actions-in-combat" in pack.rules["combat"].subsection_ids
    assert "combat" in pack.rule_sections["actions-in-combat"].rule_ids
    assert pack.skills["athletics"].ability == "str"
    assert pack.subclasses["champion"].class_id == "fighter"
    assert pack.class_levels["fighter-3"].feature_ids == ("martial-archetype",)
    assert pack.class_levels["fighter-3"].class_specific == {
        "action_surges": 1,
        "indomitable_uses": 0,
        "extra_attacks": 0,
    }
    assert pack.class_levels["wizard-5"].spellcasting is not None
    assert pack.class_levels["wizard-5"].spellcasting["spell_slots_level_3"] == 2
    assert pack.subclass_levels["champion-3"].feature_ids == ("improved-critical",)
    assert pack.subclass_levels["evocation-2"].feature_ids == (
        "evocation-savant",
        "sculpt-spells",
    )


def test_reference_pack_loads_from_decoded_data() -> None:
    pack = load_reference_pack_data(_reference_pack_data())

    assert pack.ability_scores["str"].full_name == "Strength"
    assert pack.backgrounds["wanderer"].starting_equipment == (
        BackgroundEquipment("staff", 1),
    )
    assert pack.damage_types["fire"].name == "Fire"
    assert pack.skills["athletics"].ability == "str"
    assert pack.class_levels["fighter-1"].class_specific == {"action_surges": 0}
    assert pack.subclass_levels["champion-3"].feature_ids == ("improved-critical",)


def test_reference_pack_loads_json_file(tmp_path: Path) -> None:
    path = tmp_path / "references.json"
    path.write_text(
        """
        {
          "ability_scores": [
            {"id": "str", "name": "STR", "full_name": "Strength", "skill_ids": [], "source_url": null}
          ],
          "alignments": [],
          "backgrounds": [],
          "damage_types": [],
          "equipment_categories": [],
          "magic_schools": [],
          "rules": [],
          "rule_sections": [],
          "skills": [],
          "subclasses": [],
          "class_levels": [],
          "subclass_levels": [],
          "weapon_properties": []
        }
        """,
        encoding="utf-8",
    )

    pack = load_reference_pack(path)

    assert pack.ability_scores["str"].name == "STR"


def test_reference_pack_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="missing sections"):
        load_reference_pack_data({})

    with pytest.raises(ValueError, match="unknown sections"):
        load_reference_pack_data({**_reference_pack_data(), "domains": []})

    with pytest.raises(ValueError, match="content section ability_scores must be a list"):
        load_reference_pack_data(_reference_pack_data(ability_scores={}))

    with pytest.raises(ValueError, match="entries must be objects"):
        load_reference_pack_data(_reference_pack_data(ability_scores=["str"]))

    with pytest.raises(ValueError, match="unknown fields"):
        load_reference_pack_data(
            _reference_pack_data(
                damage_types=[{"id": "fire", "name": "Fire", "source_url": None, "desc": ""}]
            )
        )

    with pytest.raises(ValueError, match="duplicate damage_types id"):
        load_reference_pack_data(
            _reference_pack_data(
                damage_types=[
                    {"id": "fire", "name": "Fire", "source_url": None},
                    {"id": "fire", "name": "Fire", "source_url": None},
                ]
            )
        )


def test_reference_definitions_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="unknown ability score"):
        AbilityScoreDefinition("luck", "LCK", "Luck")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="quantity must be positive"):
        BackgroundEquipment("staff", 0)

    with pytest.raises(ValueError, match="language choice count cannot be negative"):
        BackgroundDefinition("wanderer", "Wanderer", language_choice_count=-1)

    with pytest.raises(ValueError, match="unknown skill ability"):
        SkillDefinition("luck", "Luck", "luck")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="class level must be from 1 to 20"):
        ClassLevelDefinition("fighter-0", "fighter", 0, 2, 0)

    with pytest.raises(ValueError, match="primitive table value"):
        ClassLevelDefinition(
            "fighter-1",
            "fighter",
            1,
            2,
            0,
            class_specific={"broken": []},  # type: ignore[dict-item]
        )

    with pytest.raises(ValueError, match="subclass level must be from 1 to 20"):
        SubclassLevelDefinition("champion-0", "champion", "fighter", 0)
