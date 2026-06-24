from __future__ import annotations

from dataclasses import dataclass

from dnd5e.abilities import proficiency_bonus
from dnd5e.character import CharacterRules, ability_bonus
from dnd5e.types import Ability
from dnd5e.types import SpellComponent, SpellSchool

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
