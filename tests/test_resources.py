from typing import cast
from pathlib import Path

import pytest

from dnd5e import (
    FEATURES,
    RESOURCE_REFRESHES,
    FeatureDefinition,
    FeaturePack,
    FeatureState,
    RechargeResult,
    ResourceDefinition,
    ResourceRefresh,
    ResourceState,
    SecondWindResult,
    HitPointState,
    apply_second_wind,
    create_feature_state,
    create_resource_state,
    load_builtin_feature_pack,
    load_feature_pack,
    load_feature_pack_data,
    long_rest_feature,
    long_rest_resource,
    recharge_feature,
    recharge_resource,
    resource_maximum,
    restore_resource,
    short_rest_feature,
    short_rest_resource,
    sneak_attack_damage,
    sneak_attack_damage_dice,
    spend_feature_resource,
    spend_resource,
)


def test_public_resource_imports_and_docstrings() -> None:
    assert "short_rest" in RESOURCE_REFRESHES
    assert "second_wind" in FEATURES
    assert ResourceDefinition.__doc__
    assert ResourceState.__doc__
    assert RechargeResult.__doc__
    assert FeatureDefinition.__doc__
    assert FeaturePack.__doc__
    assert FeatureState.__doc__
    assert SecondWindResult.__doc__


def test_builtin_feature_pack_loads_current_catalog() -> None:
    pack = load_builtin_feature_pack()

    assert pack.features == FEATURES
    assert pack.features["second_wind"].resource is not None
    assert pack.features["second_wind"].resource.refresh == "short_rest"
    assert pack.features["sneak_attack"].resource is None


def test_feature_pack_loads_from_decoded_data() -> None:
    pack = load_feature_pack_data(
        {
            "features": [
                {
                    "id": "spark",
                    "name": "Spark",
                    "tags": ["fire"],
                    "resource": None,
                },
                {
                    "id": "breath",
                    "name": "Breath",
                    "tags": ["recharge"],
                    "resource": {
                        "id": "breath",
                        "name": "Breath",
                        "maximum": 1,
                        "refresh": "recharge",
                        "proficiency_based": False,
                        "recharge_minimum": 5,
                        "recharge_die": 6,
                    },
                },
            ]
        }
    )

    assert pack.features["spark"].tags == ("fire",)
    assert pack.features["spark"].resource is None
    assert pack.features["breath"].resource is not None
    assert pack.features["breath"].resource.recharge_minimum == 5


def test_feature_pack_loads_json_file(tmp_path: Path) -> None:
    path = tmp_path / "features.json"
    path.write_text(
        """
        {
          "features": [
            {
              "id": "focus",
              "name": "Focus",
              "tags": ["concentration"],
              "resource": {
                "id": "focus",
                "name": "Focus",
                "maximum": null,
                "refresh": "long_rest",
                "proficiency_based": true,
                "recharge_minimum": null,
                "recharge_die": 6
              }
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    pack = load_feature_pack(path)

    assert pack.features["focus"].resource is not None
    assert pack.features["focus"].resource.proficiency_based is True


def test_feature_pack_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="missing sections"):
        load_feature_pack_data({})

    with pytest.raises(ValueError, match="unknown sections"):
        load_feature_pack_data({"features": [], "resources": []})

    with pytest.raises(ValueError, match="content section features must be a list"):
        load_feature_pack_data({"features": {}})

    with pytest.raises(ValueError, match="entries must be objects"):
        load_feature_pack_data({"features": ["spark"]})

    with pytest.raises(ValueError, match="unknown fields"):
        load_feature_pack_data(
            {
                "features": [
                    {
                        "id": "spark",
                        "name": "Spark",
                        "tags": [],
                        "resource": None,
                        "text": "",
                    }
                ]
            }
        )

    with pytest.raises(ValueError, match="duplicate feature id"):
        load_feature_pack_data(
            {
                "features": [
                    {"id": "spark", "name": "Spark", "tags": [], "resource": None},
                    {"id": "spark", "name": "Spark", "tags": [], "resource": None},
                ]
            }
        )

    with pytest.raises(ValueError, match="feature.resource must be an object or null"):
        load_feature_pack_data(
            {
                "features": [
                    {"id": "spark", "name": "Spark", "tags": [], "resource": []},
                ]
            }
        )


def test_fixed_resource_spends_and_restores_by_rest_type() -> None:
    second_wind = FEATURES["second_wind"].resource
    assert second_wind is not None

    resource = create_resource_state(second_wind)
    spent = spend_resource(resource)
    short_rested = short_rest_resource(spent)

    assert spent.remaining == 0
    assert short_rested.remaining == 1

    rage = FEATURES["rage"].resource
    assert rage is not None
    rage_state = spend_resource(create_resource_state(rage))

    assert short_rest_resource(rage_state).remaining == 1
    assert long_rest_resource(rage_state).remaining == 2
    assert restore_resource(rage_state).remaining == 2


def test_proficiency_based_resource_uses_level_proficiency_bonus() -> None:
    resource_definition = FEATURES["proficiency_uses"].resource
    assert resource_definition is not None

    resource = create_resource_state(resource_definition, level=9)

    assert resource_maximum(resource_definition, level=9) == 4
    assert resource.maximum == 4
    assert resource.remaining == 4


def test_recharge_resource_rolls_and_restores_on_success() -> None:
    recharge = FEATURES["recharge_5_6"].resource
    assert recharge is not None
    empty = spend_resource(create_resource_state(recharge))

    failed = recharge_resource(empty, roll=4)
    succeeded = recharge_resource(empty, roll=5)

    assert failed.recharged is False
    assert failed.state.remaining == 0
    assert succeeded.recharged is True
    assert succeeded.state.remaining == 1


def test_feature_state_wraps_optional_resource_state() -> None:
    second_wind = create_feature_state(FEATURES["second_wind"])
    spent = spend_feature_resource(second_wind)
    restored = short_rest_feature(spent)

    assert second_wind.resource is not None
    assert spent.resource is not None
    assert spent.resource.remaining == 0
    assert restored.resource is not None
    assert restored.resource.remaining == 1

    sneak_attack = create_feature_state(FEATURES["sneak_attack"])

    assert sneak_attack.resource is None
    assert long_rest_feature(sneak_attack) == sneak_attack


def test_recharge_feature_returns_updated_feature_and_roll_result() -> None:
    feature = create_feature_state(FEATURES["recharge_5_6"], remaining=0)

    updated, result = recharge_feature(feature, roll=6)

    assert result.roll == 6
    assert result.recharged is True
    assert updated.resource is not None
    assert updated.resource.remaining == 1


def test_second_wind_spends_feature_and_heals_by_roll_plus_fighter_level() -> None:
    feature = create_feature_state(FEATURES["second_wind"])
    hp = HitPointState(current=4, maximum=20)

    result = apply_second_wind(feature, hp, fighter_level=5, roll=6)

    assert result.roll == 6
    assert result.feature.resource is not None
    assert result.feature.resource.remaining == 0
    assert result.healing.amount == 11
    assert result.healing.applied == 11
    assert result.healing.hit_points.current == 15


def test_second_wind_healing_caps_at_maximum_hp() -> None:
    feature = create_feature_state(FEATURES["second_wind"])
    hp = HitPointState(current=18, maximum=20)

    result = apply_second_wind(feature, hp, fighter_level=5, roll=6)

    assert result.healing.amount == 11
    assert result.healing.applied == 2
    assert result.healing.hit_points.current == 20


def test_sneak_attack_damage_scales_with_rogue_level_and_criticals() -> None:
    normal = sneak_attack_damage(rogue_level=5, damage_type="piercing", rng=lambda: 0)
    critical = sneak_attack_damage(
        rogue_level=5,
        damage_type="piercing",
        critical=True,
        rng=lambda: 0,
    )

    assert sneak_attack_damage_dice(1) == "1d6"
    assert sneak_attack_damage_dice(5) == "3d6"
    assert sneak_attack_damage_dice(20) == "10d6"
    assert normal.rolls[0].notation == "3d6"
    assert normal.total == 3
    assert critical.rolls[0].notation == "6d6"
    assert critical.total == 6


def test_resource_validation_rejects_impossible_values() -> None:
    with pytest.raises(ValueError, match="id is required"):
        ResourceDefinition("", "Test", maximum=1)

    with pytest.raises(ValueError, match="maximum is required"):
        ResourceDefinition("test", "Test", maximum=None)

    with pytest.raises(ValueError, match="unknown resource refresh"):
        ResourceDefinition("test", "Test", maximum=1, refresh=cast(ResourceRefresh, "dawn"))

    with pytest.raises(ValueError, match="recharge refresh requires recharge_minimum"):
        ResourceDefinition("test", "Test", maximum=1, refresh="recharge")

    with pytest.raises(ValueError, match="level is required"):
        create_resource_state(ResourceDefinition("test", "Test", proficiency_based=True))

    with pytest.raises(ValueError, match="not enough Test remaining"):
        spend_resource(
            ResourceState(ResourceDefinition("test", "Test", maximum=1), maximum=1, remaining=0)
        )

    with pytest.raises(ValueError, match="resource does not use recharge"):
        recharge_resource(create_resource_state(ResourceDefinition("test", "Test", maximum=1)))

    with pytest.raises(ValueError, match="feature must be Second Wind"):
        apply_second_wind(
            create_feature_state(FEATURES["rage"]),
            HitPointState(current=1, maximum=1),
            fighter_level=1,
        )

    with pytest.raises(ValueError, match="fighter_level must be from 1 to 20"):
        apply_second_wind(
            create_feature_state(FEATURES["second_wind"]),
            HitPointState(current=1, maximum=1),
            fighter_level=0,
        )

    with pytest.raises(ValueError, match="Second Wind roll must be from 1 to 10"):
        apply_second_wind(
            create_feature_state(FEATURES["second_wind"]),
            HitPointState(current=1, maximum=1),
            fighter_level=1,
            roll=11,
        )

    with pytest.raises(ValueError, match="rogue_level must be from 1 to 20"):
        sneak_attack_damage_dice(0)


def test_feature_validation_rejects_invalid_resource_pairings() -> None:
    with pytest.raises(ValueError, match="feature tags cannot be empty"):
        FeatureDefinition("test", "Test", tags=("",))

    with pytest.raises(ValueError, match="has no limited-use resource"):
        spend_feature_resource(create_feature_state(FEATURES["pack_tactics"]))

    with pytest.raises(ValueError, match="resource state requires"):
        FeatureState(
            definition=FEATURES["pack_tactics"],
            resource=create_resource_state(ResourceDefinition("test", "Test", maximum=1)),
        )

    with pytest.raises(ValueError, match="does not match"):
        FeatureState(
            definition=FEATURES["second_wind"],
            resource=create_resource_state(ResourceDefinition("test", "Test", maximum=1)),
        )
