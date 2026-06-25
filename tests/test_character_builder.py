from examples.character_builder import build_character, catalog_options


def test_character_builder_options_expose_content_catalogs() -> None:
    options = catalog_options()

    assert "fighter" in {entry["name"] for entry in options["classes"]}
    assert "human" in {entry["id"] for entry in options["races"]}
    assert "longsword" in {entry["id"] for entry in options["weapons"]}


def test_character_builder_builds_library_backed_summary() -> None:
    summary = build_character(
        {
            "name": "Kara",
            "class": "fighter",
            "level": 5,
            "race": "human",
            "languageChoices": ["elvish"],
            "skills": ["athletics", "perception"],
            "abilities": {
                "str": 15,
                "dex": 13,
                "con": 13,
                "int": 9,
                "wis": 11,
                "cha": 7,
            },
            "armor": "chain_mail",
            "shield": "shield",
            "weapons": ["longsword", "shortbow"],
            "twoHandedWeapons": ["longsword"],
        }
    )

    assert summary["sheet"]["name"] == "Kara"
    assert summary["sheet"]["abilities"]["str"] == 16
    assert summary["derived"]["armorClass"]["total"] == 18
    assert summary["derived"]["hitPoints"]["maximum"] == 44
    assert summary["derived"]["attacks"][0]["attack_bonus"] == 6
    assert summary["derived"]["progression"]["features"][1]["id"] == "second_wind"
    assert summary["derived"]["spellcasting"] is None
