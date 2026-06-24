from __future__ import annotations

from dataclasses import dataclass
from random import random

from dnd5e.abilities import RandomSource, d20_check, proficiency_bonus
from dnd5e.character import ABILITIES, CharacterRules, ability_bonus
from dnd5e.combat import (
    AttackActionResult,
    CombatState,
    Combatant,
    DamageResult,
    apply_combat_damage,
    apply_combat_healing,
    apply_condition as apply_combat_condition,
    combatant_by_id,
    damage_roll,
    resolve_attack_action,
)
from dnd5e.effects import (
    combine_advantage,
    condition_auto_fails_save,
    condition_saving_throw_modifier,
)
from dnd5e.hit_points import DamageApplicationResult, HealingResult
from dnd5e.types import Ability
from dnd5e.types import AdvantageState, ConditionName, DamageType, SpellComponent, SpellSchool

SPELL_SCHOOLS: tuple[SpellSchool, ...] = (
    "abjuration",
    "conjuration",
    "divination",
    "enchantment",
    "evocation",
    "illusion",
    "necromancy",
    "transmutation",
)
SPELL_COMPONENTS: tuple[SpellComponent, ...] = ("verbal", "somatic", "material")


@dataclass(frozen=True)
class SpellDefinition:
    """Spell metadata for casting rules, slots, and later effect handling."""

    id: str
    name: str
    level: int
    school: SpellSchool
    casting_time: str
    range: str
    duration: str
    components: tuple[SpellComponent, ...]
    concentration: bool = False
    ritual: bool = False
    material: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("spell id is required")
        if not self.name:
            raise ValueError("spell name is required")
        if not 0 <= self.level <= 9:
            raise ValueError("spell level must be from 0 to 9")
        if self.school not in SPELL_SCHOOLS:
            raise ValueError(f"unknown spell school: {self.school}")
        _validate_non_empty("casting_time", self.casting_time)
        _validate_non_empty("range", self.range)
        _validate_non_empty("duration", self.duration)
        if not self.components:
            raise ValueError("spell components are required")
        for component in self.components:
            if component not in SPELL_COMPONENTS:
                raise ValueError(f"unknown spell component: {component}")
        if self.material and "material" not in self.components:
            raise ValueError("material detail requires a material component")
        if self.material == "":
            raise ValueError("material detail cannot be empty")


@dataclass(frozen=True)
class SpellSlotPool:
    """One spell level's expended and available spell slots."""

    level: int
    maximum: int
    remaining: int

    def __post_init__(self) -> None:
        _validate_spell_slot_level(self.level)
        _validate_positive("maximum spell slots", self.maximum)
        if not 0 <= self.remaining <= self.maximum:
            raise ValueError("remaining spell slots must be from 0 to maximum spell slots")


@dataclass(frozen=True)
class SpellSlotState:
    """Runtime spell slot pools for prepared or known spellcasting."""

    slots: tuple[SpellSlotPool, ...]

    def __post_init__(self) -> None:
        seen: set[int] = set()
        for slot in self.slots:
            if slot.level in seen:
                raise ValueError(f"duplicate spell slot level: {slot.level}")
            seen.add(slot.level)


@dataclass(frozen=True)
class PactMagicState:
    """Runtime pact magic slots that share one slot level."""

    slot_level: int
    maximum: int
    remaining: int

    def __post_init__(self) -> None:
        if not 1 <= self.slot_level <= 5:
            raise ValueError("pact magic slot level must be from 1 to 5")
        _validate_positive("maximum pact magic slots", self.maximum)
        if not 0 <= self.remaining <= self.maximum:
            raise ValueError("remaining pact magic slots must be from 0 to maximum pact magic slots")


@dataclass(frozen=True)
class SavingThrowResult:
    """Resolved saving throw against a spell or other forced DC."""

    ability: Ability
    roll: int
    total: int
    dc: int
    success: bool
    discarded_roll: int | None = None

    def __post_init__(self) -> None:
        if self.ability not in ABILITIES:
            raise ValueError(f"unknown saving throw ability: {self.ability}")
        _validate_d20(self.roll, "saving throw roll")
        if self.discarded_roll is not None:
            _validate_d20(self.discarded_roll, "discarded saving throw roll")
        if self.dc < 1:
            raise ValueError("saving throw DC must be positive")


@dataclass(frozen=True)
class SpellSaveDamageResult:
    """Spell event for save-based damage, including any HP application."""

    state: CombatState
    target_before: Combatant
    target_after: Combatant
    save: SavingThrowResult
    damage: DamageResult | None = None
    damage_application: DamageApplicationResult | None = None


@dataclass(frozen=True)
class SpellHealingResult:
    """Spell event for rolled healing applied to one combatant."""

    state: CombatState
    target_before: Combatant
    target_after: Combatant
    roll: DamageResult
    healing: HealingResult


@dataclass(frozen=True)
class SpellConditionResult:
    """Spell event for applying a condition, optionally gated by a failed save."""

    state: CombatState
    target_before: Combatant
    target_after: Combatant
    condition: ConditionName
    applied: bool
    save: SavingThrowResult | None = None


def _validate_non_empty(name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{name} is required")


def create_spell_slots(maximums: dict[int, int]) -> SpellSlotState:
    """Create a full spell slot state from maximum slots by spell level."""

    return SpellSlotState(
        tuple(
            SpellSlotPool(level=level, maximum=maximum, remaining=maximum)
            for level, maximum in sorted(maximums.items())
        )
    )


def spell_slots_remaining(state: SpellSlotState, level: int) -> int:
    """Return remaining slots for a spell level, or zero if that level has no pool."""

    _validate_spell_slot_level(level)
    pool = _spell_slot_pool(state, level)
    if pool is None:
        return 0
    return pool.remaining


def spend_spell_slot(state: SpellSlotState, level: int) -> SpellSlotState:
    """Spend one spell slot of the requested level and return updated state."""

    _validate_spell_slot_level(level)
    pool = _spell_slot_pool(state, level)
    if pool is None or pool.remaining <= 0:
        raise ValueError(f"no spell slots remaining for level {level}")

    return SpellSlotState(
        tuple(
            SpellSlotPool(slot.level, slot.maximum, slot.remaining - 1)
            if slot.level == level
            else slot
            for slot in state.slots
        )
    )


def restore_spell_slots(state: SpellSlotState) -> SpellSlotState:
    """Restore all spell slots to their maximum values."""

    return SpellSlotState(
        tuple(SpellSlotPool(slot.level, slot.maximum, slot.maximum) for slot in state.slots)
    )


def create_pact_magic(slot_level: int, maximum: int) -> PactMagicState:
    """Create full pact magic state for slots that all share one slot level."""

    return PactMagicState(slot_level=slot_level, maximum=maximum, remaining=maximum)


def spend_pact_slot(state: PactMagicState) -> PactMagicState:
    """Spend one pact magic slot and return updated state."""

    if state.remaining <= 0:
        raise ValueError("no pact magic slots remaining")
    return PactMagicState(
        slot_level=state.slot_level,
        maximum=state.maximum,
        remaining=state.remaining - 1,
    )


def restore_pact_magic(state: PactMagicState) -> PactMagicState:
    """Restore pact magic slots to their maximum value."""

    return PactMagicState(
        slot_level=state.slot_level,
        maximum=state.maximum,
        remaining=state.maximum,
    )


def spell_attack_bonus(character: CharacterRules, ability: Ability, bonus: int = 0) -> int:
    """Return spell attack bonus from ability modifier, proficiency, and flat bonuses."""

    return _spellcasting_bonus(character, ability, bonus)


def spell_save_dc(character: CharacterRules, ability: Ability, bonus: int = 0) -> int:
    """Return spell save DC from the standard base DC, ability, proficiency, and bonuses."""

    return 8 + _spellcasting_bonus(character, ability, bonus)


def saving_throw(
    *,
    ability: Ability,
    save_bonus: int,
    dc: int,
    roll: int | None = None,
    advantage: AdvantageState = "normal",
    conditions: tuple[ConditionName, ...] = (),
    rng: RandomSource = random,
) -> SavingThrowResult:
    """Resolve a saving throw against a fixed DC."""

    if dc < 1:
        raise ValueError("saving throw DC must be positive")
    condition_modifier = condition_saving_throw_modifier(conditions, ability)
    check = d20_check(
        ability_score=10,
        bonus=save_bonus,
        roll=roll,
        advantage=combine_advantage(advantage, condition_modifier.advantage),
        rng=rng,
    )
    return SavingThrowResult(
        ability=ability,
        roll=check.roll,
        discarded_roll=check.discarded_roll,
        total=check.total,
        dc=dc,
        success=check.total >= dc and not condition_auto_fails_save(conditions, ability),
    )


def resolve_spell_attack(
    state: CombatState,
    *,
    actor_id: str,
    target_id: str,
    attack_bonus: int,
    damage_dice: str,
    damage_type: DamageType,
    roll: int | None = None,
    advantage: AdvantageState = "normal",
    damage_rng: RandomSource = random,
    attack_rng: RandomSource = random,
    bonus_dice: tuple[str, ...] = (),
) -> AttackActionResult:
    """Resolve a single-target spell attack and apply damage on a hit."""

    return resolve_attack_action(
        state,
        actor_id=actor_id,
        target_id=target_id,
        attack_bonus=attack_bonus,
        damage_dice=damage_dice,
        damage_type=damage_type,
        roll=roll,
        advantage=advantage,
        damage_rng=damage_rng,
        attack_rng=attack_rng,
        bonus_dice=bonus_dice,
    )


def resolve_spell_save_damage(
    state: CombatState,
    *,
    target_id: str,
    save_ability: Ability,
    save_bonus: int,
    save_dc: int,
    damage_dice: str,
    damage_type: DamageType,
    roll: int | None = None,
    advantage: AdvantageState = "normal",
    save_rng: RandomSource = random,
    damage_rng: RandomSource = random,
    half_damage_on_success: bool = False,
) -> SpellSaveDamageResult:
    """Resolve save-based spell damage and apply none, half, or full damage."""

    target = combatant_by_id(state, target_id)
    save = saving_throw(
        ability=save_ability,
        save_bonus=save_bonus,
        dc=save_dc,
        roll=roll,
        advantage=advantage,
        conditions=target.conditions,
        rng=save_rng,
    )

    if save.success and not half_damage_on_success:
        return SpellSaveDamageResult(
            state=state,
            target_before=target,
            target_after=target,
            save=save,
        )

    damage = damage_roll(dice=damage_dice, type=damage_type, rng=damage_rng)
    amount = damage.total // 2 if save.success else damage.total
    application = apply_combat_damage(state, target_id=target_id, amount=amount, damage_type=damage_type)
    return SpellSaveDamageResult(
        state=application.state,
        target_before=target,
        target_after=application.target_after,
        save=save,
        damage=damage,
        damage_application=application.damage_application,
    )


def apply_spell_healing(
    state: CombatState,
    *,
    target_id: str,
    healing_dice: str,
    healing_rng: RandomSource = random,
) -> SpellHealingResult:
    """Roll spell healing dice and apply the total to one combatant."""

    target = combatant_by_id(state, target_id)
    healing_roll = damage_roll(dice=healing_dice, type="radiant", rng=healing_rng)
    healing = apply_combat_healing(state, target_id=target_id, amount=healing_roll.total)
    return SpellHealingResult(
        state=healing.state,
        target_before=target,
        target_after=healing.target_after,
        roll=healing_roll,
        healing=healing.healing,
    )


def apply_spell_condition(
    state: CombatState,
    *,
    target_id: str,
    condition: ConditionName,
    save_ability: Ability | None = None,
    save_bonus: int = 0,
    save_dc: int | None = None,
    roll: int | None = None,
    advantage: AdvantageState = "normal",
    save_rng: RandomSource = random,
) -> SpellConditionResult:
    """Apply a spell condition directly, or only after a failed saving throw."""

    target = combatant_by_id(state, target_id)
    save = None
    if save_ability is not None:
        if save_dc is None:
            raise ValueError("save_dc is required when save_ability is provided")
        save = saving_throw(
            ability=save_ability,
            save_bonus=save_bonus,
            dc=save_dc,
            roll=roll,
            advantage=advantage,
            conditions=target.conditions,
            rng=save_rng,
        )
        if save.success:
            return SpellConditionResult(
                state=state,
                target_before=target,
                target_after=target,
                condition=condition,
                applied=False,
                save=save,
            )

    next_state = apply_combat_condition(state, target_id=target_id, condition=condition)
    target_after = combatant_by_id(next_state, target_id)
    return SpellConditionResult(
        state=next_state,
        target_before=target,
        target_after=target_after,
        condition=condition,
        applied=target_after.conditions != target.conditions,
        save=save,
    )


def _spellcasting_bonus(character: CharacterRules, ability: Ability, bonus: int) -> int:
    return ability_bonus(character, ability) + proficiency_bonus(character.level) + bonus


def _spell_slot_pool(state: SpellSlotState, level: int) -> SpellSlotPool | None:
    for slot in state.slots:
        if slot.level == level:
            return slot
    return None


def _validate_spell_slot_level(level: int) -> None:
    if not 1 <= level <= 9:
        raise ValueError("spell slot level must be from 1 to 9")


def _validate_d20(value: int, context: str) -> None:
    if not 1 <= value <= 20:
        raise ValueError(f"{context} must be from 1 to 20")


def _validate_positive(name: str, value: int) -> None:
    if value < 1:
        raise ValueError(f"{name} must be positive")


SPELLS: dict[str, SpellDefinition] = {
    "cure_wounds": SpellDefinition(
        id="cure_wounds",
        name="Cure Wounds",
        level=1,
        school="evocation",
        casting_time="1 action",
        range="touch",
        duration="instantaneous",
        components=("verbal", "somatic"),
    ),
    "detect_magic": SpellDefinition(
        id="detect_magic",
        name="Detect Magic",
        level=1,
        school="divination",
        casting_time="1 action",
        range="self",
        duration="10 minutes",
        components=("verbal", "somatic"),
        concentration=True,
        ritual=True,
    ),
    "fire_bolt": SpellDefinition(
        id="fire_bolt",
        name="Fire Bolt",
        level=0,
        school="evocation",
        casting_time="1 action",
        range="120 feet",
        duration="instantaneous",
        components=("verbal", "somatic"),
    ),
    "light": SpellDefinition(
        id="light",
        name="Light",
        level=0,
        school="evocation",
        casting_time="1 action",
        range="touch",
        duration="1 hour",
        components=("verbal", "material"),
        material="phosphorescent moss or firefly",
    ),
    "mage_armor": SpellDefinition(
        id="mage_armor",
        name="Mage Armor",
        level=1,
        school="abjuration",
        casting_time="1 action",
        range="touch",
        duration="8 hours",
        components=("verbal", "somatic", "material"),
        material="cured leather",
    ),
    "sacred_flame": SpellDefinition(
        id="sacred_flame",
        name="Sacred Flame",
        level=0,
        school="evocation",
        casting_time="1 action",
        range="60 feet",
        duration="instantaneous",
        components=("verbal", "somatic"),
    ),
}
