import pytest

from dnd5e import (
    CREATURES,
    XP_BY_CHALLENGE_RATING,
    EncounterMonster,
    EncounterSummary,
    EncounterThresholds,
    challenge_rating_xp,
    encounter_difficulty,
    encounter_monster,
    encounter_xp_multiplier,
    party_xp_thresholds,
    summarize_encounter,
)


def test_public_encounter_imports_and_docstrings() -> None:
    assert XP_BY_CHALLENGE_RATING["1/4"] == 50
    assert EncounterThresholds.__doc__
    assert EncounterMonster.__doc__
    assert EncounterSummary.__doc__


def test_challenge_rating_xp_uses_srd_xp_table() -> None:
    assert challenge_rating_xp("0") == 10
    assert challenge_rating_xp("1/8") == 25
    assert challenge_rating_xp("1/4") == 50
    assert challenge_rating_xp("5") == 1800


def test_challenge_rating_xp_rejects_unknown_cr() -> None:
    with pytest.raises(ValueError, match="unknown challenge rating"):
        challenge_rating_xp("1/3")


def test_encounter_monster_accepts_catalog_ids_and_counts_xp() -> None:
    goblins = encounter_monster("goblin", count=3)

    assert goblins.definition is CREATURES["goblin"]
    assert goblins.count == 3
    assert goblins.xp == 150


def test_encounter_monster_rejects_impossible_count() -> None:
    with pytest.raises(ValueError, match="monster count must be positive"):
        encounter_monster("goblin", count=0)


def test_encounter_xp_multiplier_steps_by_monster_count() -> None:
    assert encounter_xp_multiplier(1) == 1
    assert encounter_xp_multiplier(2) == 1.5
    assert encounter_xp_multiplier(3) == 2
    assert encounter_xp_multiplier(7) == 2.5
    assert encounter_xp_multiplier(11) == 3
    assert encounter_xp_multiplier(15) == 4


def test_party_xp_thresholds_sum_character_levels() -> None:
    thresholds = party_xp_thresholds([1, 1, 2, 2])

    assert thresholds == EncounterThresholds(easy=150, medium=300, hard=450, deadly=600)


def test_party_xp_thresholds_rejects_missing_or_invalid_levels() -> None:
    with pytest.raises(ValueError, match="party levels are required"):
        party_xp_thresholds([])

    with pytest.raises(ValueError, match="party levels must be from 1 to 20"):
        party_xp_thresholds([0])

    with pytest.raises(ValueError, match="party levels must be from 1 to 20"):
        party_xp_thresholds([21])


def test_encounter_difficulty_compares_adjusted_xp_to_thresholds() -> None:
    thresholds = EncounterThresholds(easy=100, medium=200, hard=300, deadly=400)

    assert encounter_difficulty(50, thresholds) == "trivial"
    assert encounter_difficulty(100, thresholds) == "easy"
    assert encounter_difficulty(200, thresholds) == "medium"
    assert encounter_difficulty(300, thresholds) == "hard"
    assert encounter_difficulty(400, thresholds) == "deadly"


def test_summarize_encounter_calculates_xp_thresholds_and_difficulty() -> None:
    summary = summarize_encounter(
        [
            encounter_monster("goblin", count=3),
            encounter_monster("wolf"),
        ],
        party_levels=[1, 1, 1, 1],
    )

    assert summary.monster_count == 4
    assert summary.total_xp == 200
    assert summary.xp_multiplier == 2
    assert summary.adjusted_xp == 400
    assert summary.thresholds == EncounterThresholds(easy=100, medium=200, hard=300, deadly=400)
    assert summary.difficulty == "deadly"


def test_summarize_encounter_preserves_fractional_adjusted_xp() -> None:
    summary = summarize_encounter(
        [
            encounter_monster("goblin"),
            encounter_monster("cultist"),
        ],
        party_levels=[1, 1],
    )

    assert summary.total_xp == 75
    assert summary.xp_multiplier == 1.5
    assert summary.adjusted_xp == 112.5


def test_summarize_encounter_uses_expanded_creature_catalog() -> None:
    summary = summarize_encounter(
        [
            encounter_monster("ogre"),
            encounter_monster("bandit", count=2),
        ],
        party_levels=[3, 3, 3, 3],
    )

    assert summary.monster_count == 3
    assert summary.total_xp == 500
    assert summary.xp_multiplier == 2
    assert summary.adjusted_xp == 1000
    assert summary.difficulty == "hard"


def test_summarize_encounter_uses_new_low_and_mid_cr_creatures() -> None:
    summary = summarize_encounter(
        [
            encounter_monster("bugbear"),
            encounter_monster("orc"),
            encounter_monster("kobold", count=2),
        ],
        party_levels=[2, 2, 2, 2],
    )

    assert summary.monster_count == 4
    assert summary.total_xp == 350
    assert summary.xp_multiplier == 2
    assert summary.adjusted_xp == 700
    assert summary.difficulty == "hard"


def test_summarize_encounter_rejects_empty_monsters() -> None:
    with pytest.raises(ValueError, match="encounter requires at least one monster"):
        summarize_encounter([], party_levels=[1])
