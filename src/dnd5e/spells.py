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


def _validate_non_empty(name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{name} is required")


def spell_attack_bonus(character: CharacterRules, ability: Ability, bonus: int = 0) -> int:
    """Return spell attack bonus from ability modifier, proficiency, and flat bonuses."""

    return _spellcasting_bonus(character, ability, bonus)


def spell_save_dc(character: CharacterRules, ability: Ability, bonus: int = 0) -> int:
    """Return spell save DC from the standard base DC, ability, proficiency, and bonuses."""

    return 8 + _spellcasting_bonus(character, ability, bonus)


def _spellcasting_bonus(character: CharacterRules, ability: Ability, bonus: int) -> int:
    return ability_bonus(character, ability) + proficiency_bonus(character.level) + bonus


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
