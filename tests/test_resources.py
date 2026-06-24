from typing import cast

import pytest

from dnd5e import (
    FEATURES,
    RESOURCE_REFRESHES,
    FeatureDefinition,
    FeatureState,
    RechargeResult,
    ResourceDefinition,
    ResourceRefresh,
    ResourceState,
    create_feature_state,
    create_resource_state,
    long_rest_feature,
    long_rest_resource,
    recharge_feature,
    recharge_resource,
    resource_maximum,
    restore_resource,
    short_rest_feature,
    short_rest_resource,
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
    assert FeatureState.__doc__


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
        spend_resource(ResourceState(ResourceDefinition("test", "Test", maximum=1), maximum=1, remaining=0))

    with pytest.raises(ValueError, match="resource does not use recharge"):
        recharge_resource(create_resource_state(ResourceDefinition("test", "Test", maximum=1)))


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
