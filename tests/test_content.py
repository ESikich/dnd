from pathlib import Path

import pytest

from dnd5e import (
    CONTENT_PACK_SECTIONS,
    ARMOR,
    SPELLS,
    ContentPack,
    load_builtin_content_pack,
    load_content_pack,
    load_content_pack_data,
)


def test_public_content_imports_and_docstrings() -> None:
    assert "equipment" in CONTENT_PACK_SECTIONS
    assert "encounter_rules" in CONTENT_PACK_SECTIONS
    assert ContentPack.__doc__


def test_builtin_content_pack_loads_all_packaged_domains() -> None:
    pack = load_builtin_content_pack()

    assert pack.equipment is not None
    assert pack.equipment.armor["leather"] == ARMOR["leather"]
    assert pack.spells is not None
    assert pack.spells.spells["fire_bolt"] == SPELLS["fire_bolt"]
    assert pack.classes is not None
    assert pack.creatures is not None
    assert pack.features is not None
    assert pack.conditions is not None
    assert pack.encounter_rules is not None


def test_content_pack_data_loads_supported_section_subset() -> None:
    pack = load_content_pack_data(
        {
            "equipment": {
                "armor": [
                    {
                        "id": "training_leather",
                        "name": "Training Leather",
                        "category": "light",
                        "base_ac": 11,
                        "cost_cp": 0,
                        "weight_lb": 8,
                        "max_dex_bonus": None,
                        "strength_requirement": None,
                        "stealth_disadvantage": False,
                    }
                ],
                "shields": [],
                "weapons": [],
            },
            "spells": {
                "spells": [
                    {
                        "id": "spark",
                        "name": "Spark",
                        "level": 0,
                        "school": "evocation",
                        "casting_time": "1 action",
                        "range": "30 feet",
                        "duration": "instantaneous",
                        "components": ["somatic"],
                        "concentration": False,
                        "ritual": False,
                        "material": None,
                    }
                ]
            },
        }
    )

    assert pack.equipment is not None
    assert pack.equipment.armor["training_leather"].base_ac == 11
    assert pack.spells is not None
    assert pack.spells.spells["spark"].components == ("somatic",)
    assert pack.classes is None
    assert pack.creatures is None


def test_content_pack_loads_json_file(tmp_path: Path) -> None:
    path = tmp_path / "content.json"
    path.write_text(
        """
        {
          "features": {
            "features": [
              {
                "id": "focus",
                "name": "Focus",
                "tags": ["concentration"],
                "resource": null
              }
            ]
          }
        }
        """,
        encoding="utf-8",
    )

    pack = load_content_pack(path)

    assert pack.features is not None
    assert pack.features.features["focus"].tags == ("concentration",)


def test_content_pack_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="requires at least one content section"):
        load_content_pack_data({})

    with pytest.raises(ValueError, match="unknown sections"):
        load_content_pack_data({"treasure": {}})

    with pytest.raises(ValueError, match="section spells must be a JSON object"):
        load_content_pack_data({"spells": []})

    with pytest.raises(ValueError, match="spell content pack missing sections"):
        load_content_pack_data({"spells": {}})
