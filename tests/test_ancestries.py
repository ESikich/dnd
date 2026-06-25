from pathlib import Path

import pytest

from dnd5e import (
    LANGUAGES,
    PROFICIENCIES,
    RACES,
    SUBRACES,
    AncestryAbilityBonus,
    AncestryPack,
    LanguageDefinition,
    ProficiencyDefinition,
    RaceDefinition,
    SubraceDefinition,
    load_ancestry_pack,
    load_ancestry_pack_data,
    load_builtin_ancestry_pack,
    race_ability_bonuses,
    race_languages,
)


def _race_entry(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "id": "testfolk",
        "name": "Testfolk",
        "speed": 30,
        "size": "medium",
        "ability_bonuses": [{"ability": "dex", "bonus": 2}],
        "ability_bonus_options": [],
        "ability_bonus_choice_count": 0,
        "languages": ["common"],
        "language_options": [],
        "language_choice_count": 0,
        "traits": ["test-trait"],
        "subraces": [],
        "source_url": None,
    }
    values.update(overrides)
    return values


def _ancestry_pack_data(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "races": [_race_entry()],
        "subraces": [
            {
                "id": "quick-testfolk",
                "name": "Quick Testfolk",
                "race_id": "testfolk",
                "ability_bonuses": [{"ability": "int", "bonus": 1}],
                "traits": ["quick"],
                "source_url": None,
            }
        ],
        "languages": [
            {
                "id": "common",
                "name": "Common",
                "type": "Standard",
                "script": "Common",
                "typical_speakers": ["Humans"],
                "source_url": None,
            }
        ],
        "proficiencies": [
            {
                "id": "longswords",
                "name": "Longswords",
                "type": "Weapons",
                "reference_id": "longsword",
                "reference_url": "/api/2014/equipment/longsword",
                "class_ids": [],
                "race_ids": ["testfolk"],
                "source_url": None,
            }
        ],
    }
    values.update(overrides)
    return values


def test_public_ancestry_imports_and_docstrings() -> None:
    assert isinstance(RACES["elf"], RaceDefinition)
    assert isinstance(SUBRACES["high-elf"], SubraceDefinition)
    assert isinstance(LANGUAGES["common"], LanguageDefinition)
    assert isinstance(PROFICIENCIES["longswords"], ProficiencyDefinition)
    assert isinstance(load_builtin_ancestry_pack(), AncestryPack)
    assert AncestryAbilityBonus.__doc__
    assert RaceDefinition.__doc__


def test_builtin_ancestry_pack_loads_srd_catalogs() -> None:
    pack = load_builtin_ancestry_pack()

    assert pack.races == RACES
    assert len(pack.races) == 9
    assert len(pack.subraces) == 4
    assert len(pack.languages) == 16
    assert len(pack.proficiencies) == 117
    assert pack.races["dragonborn"].ability_bonuses == (
        AncestryAbilityBonus("str", 2),
        AncestryAbilityBonus("cha", 1),
    )
    assert pack.races["half-elf"].ability_bonus_choice_count == 2
    assert pack.races["human"].language_choice_count == 1
    assert pack.subraces["high-elf"].race_id == "elf"
    assert pack.languages["abyssal"].script == "Infernal"
    assert pack.proficiencies["longswords"].reference_id == "longsword"


def test_ancestry_pack_loads_from_decoded_data() -> None:
    pack = load_ancestry_pack_data(_ancestry_pack_data())

    assert pack.races["testfolk"].ability_bonuses[0] == AncestryAbilityBonus("dex", 2)
    assert pack.subraces["quick-testfolk"].traits == ("quick",)
    assert pack.languages["common"].typical_speakers == ("Humans",)
    assert pack.proficiencies["longswords"].race_ids == ("testfolk",)


def test_ancestry_pack_loads_json_file(tmp_path: Path) -> None:
    path = tmp_path / "ancestries.json"
    path.write_text(
        """
        {
          "races": [
            {
              "id": "testfolk",
              "name": "Testfolk",
              "speed": 30,
              "size": "medium",
              "ability_bonuses": [{"ability": "dex", "bonus": 2}],
              "ability_bonus_options": [],
              "ability_bonus_choice_count": 0,
              "languages": ["common"],
              "language_options": [],
              "language_choice_count": 0,
              "traits": [],
              "subraces": [],
              "source_url": null
            }
          ],
          "subraces": [],
          "languages": [],
          "proficiencies": []
        }
        """,
        encoding="utf-8",
    )

    pack = load_ancestry_pack(path)

    assert pack.races["testfolk"].speed == 30


def test_race_ability_bonuses_combines_race_subrace_and_choices() -> None:
    assert race_ability_bonuses("elf", subrace="high-elf") == {"dex": 2, "int": 1}
    assert race_ability_bonuses("half-elf", ability_choices=("str", "int")) == {
        "cha": 2,
        "str": 1,
        "int": 1,
    }


def test_race_languages_combines_fixed_and_choice_languages() -> None:
    assert race_languages("human", language_choices=("elvish",)) == ("common", "elvish")
    assert race_languages("half-elf", language_choices=("draconic",)) == (
        "common",
        "elvish",
        "draconic",
    )


def test_ancestry_pack_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="missing sections"):
        load_ancestry_pack_data({})

    with pytest.raises(ValueError, match="unknown sections"):
        load_ancestry_pack_data({**_ancestry_pack_data(), "lineages": []})

    with pytest.raises(ValueError, match="content section races must be a list"):
        load_ancestry_pack_data(_ancestry_pack_data(races={}))

    with pytest.raises(ValueError, match="entries must be objects"):
        load_ancestry_pack_data(_ancestry_pack_data(races=["elf"]))

    with pytest.raises(ValueError, match="unknown fields"):
        load_ancestry_pack_data(_ancestry_pack_data(races=[{**_race_entry(), "desc": ""}]))

    with pytest.raises(ValueError, match="duplicate race id"):
        load_ancestry_pack_data(_ancestry_pack_data(races=[_race_entry(), _race_entry()]))


def test_ancestry_definitions_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="unknown ability"):
        AncestryAbilityBonus("luck", 1)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="race speed cannot be negative"):
        load_ancestry_pack_data(_ancestry_pack_data(races=[_race_entry(speed=-1)]))

    with pytest.raises(ValueError, match="unknown race size"):
        load_ancestry_pack_data(_ancestry_pack_data(races=[_race_entry(size="middling")]))

    with pytest.raises(ValueError, match="choice count cannot exceed"):
        load_ancestry_pack_data(
            _ancestry_pack_data(races=[_race_entry(ability_bonus_choice_count=1)])
        )


def test_race_helpers_reject_invalid_choices() -> None:
    with pytest.raises(ValueError, match="incorrect number of ability choices"):
        race_ability_bonuses("half-elf", ability_choices=("str",))

    with pytest.raises(ValueError, match="ability choices must be unique"):
        race_ability_bonuses("half-elf", ability_choices=("str", "str"))

    with pytest.raises(ValueError, match="invalid ability choice"):
        race_ability_bonuses("half-elf", ability_choices=("str", "cha"))

    with pytest.raises(ValueError, match="subrace does not belong"):
        race_ability_bonuses("dwarf", subrace="high-elf")

    with pytest.raises(ValueError, match="incorrect number of language choices"):
        race_languages("human")

    with pytest.raises(ValueError, match="invalid language choices"):
        race_languages("human", language_choices=("made-up",))
