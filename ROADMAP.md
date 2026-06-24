# D&D 5E Rules Library Roadmap

This roadmap is the working plan for turning the current mechanics helpers into
a complete 5E-compatible rules library. Each phase should be implemented with
focused public APIs, tests, and a small demo update.

## Current State

Implemented:

- Dice notation parsing and rolling
- Ability modifiers, proficiency, d20 checks, passive scores
- Skill and saving throw helpers
- Initiative ordering and turn advancement
- Attack rolls and damage rolls
- Equipment, armor, shields, weapons, AC, weapon attack profiles
- HP, healing, temporary HP, hit dice, rests, death saves
- Basic creature/stat block definitions for a small SRD-style catalog
- Creature stat block validation for impossible HP, AC, ability scores, dice, movement, senses, and XP
- SRD-style class metadata
- Condition metadata as tags
- Character sheets with class levels, loadouts, validation, derived HP, AC, skills, saves, attacks, and combatants
- HP state, hit dice pool, and death save state validation for impossible values
- Core character rules validation for impossible levels, missing or invalid ability scores, invalid proficiency choices, and invalid skill/save bonus keys
- A deterministic example program with a tiny battle
- Combat runtime state with HP, AC, conditions, healing, and attack action resolution

## Phase 1: Rules Foundation Polish

Goal: make the existing foundation consistent and dependable before adding
larger systems.

Todo:

- Review naming consistency across modules.
- Add validation for impossible HP, ability scores, dice pools, and equipment IDs.
- Add richer docstrings for public dataclasses and functions.
- Refresh `README.md` examples so they show current features.
- Consider adding `ruff` and `mypy` commands once the public shapes settle.

Progress:

- Done: character sheets validate loadout equipment IDs before derived AC or attack helpers run.
- Done: HP state, hit dice pool, and death save state objects validate impossible values at construction.
- Done: public HP dataclasses have docstrings describing their mechanics role.
- Done: `CharacterRules` validates level, ability score maps, proficiency choices, and skill/save bonus keys at construction.
- Done: creature actions and definitions validate impossible dice, HP, AC, ability scores, ranges, movement, senses, and XP at construction.
- Done: public creature dataclasses have docstrings describing their mechanics role.
- Done: public dice and d20 helper dataclasses/functions have docstrings describing their mechanics role.
- Done: README examples show current character-sheet and creature combatant helpers.
- Done: dice notation and d20 input validation paths are covered by focused tests.

Done when:

- Existing modules are documented and tested.
- The README accurately reflects the current API.
- `python3 -m pytest` passes.

## Phase 2: Combat Runtime With HP

Goal: replace scripted demo battle bookkeeping with reusable combat state.

Progress:

- Done: add combatant runtime state: id, name, AC, HP, initiative, conditions, source definition.
- Done: add helpers to create runtime combatants and creature runtime combatants.
- Done: add attack action resolution that rolls attack, rolls damage on hit, applies HP damage, and returns an event/result object.
- Done: add healing and condition application helpers.
- Done: add defeated/downed detection.
- Done: keep turn advancement compatible with the existing initiative model.
- Done: update the tiny battle demo to use the combat runtime instead of local HP dictionaries.
- Done: add a character-sheet combatant constructor backed by derived loadout AC and HP.

Deferred:

- Add more action event shapes as reactions, saves, resources, and effects come online.

Done when:

- A small fight can be run with library state objects.
- Tests cover hit, miss, critical hit, damage application, defeat, and turn advancement.

## Phase 3: Character Sheet Model

Goal: turn loose character helpers into a fuller character representation.

Progress:

- Done: add character sheet dataclasses for class levels, abilities, proficiencies, equipment loadout, HP, and notes.
- Done: add derived stat helpers for AC, initiative, skills, saves, passive skills, attack profiles, and max HP.
- Done: add class-level structures and multiclass placeholders.
- Done: add equipment loadout support.
- Done: add validation for missing abilities, invalid ability scores, invalid total level, and impossible HP.
- Done: add validation for invalid skill and saving throw proficiency choices.
- Done: add broader tests for common invalid sheets.

Done when:

- A character sheet can produce the values currently assembled manually in the demo.
- Tests cover derived stats and common invalid sheets. Complete.

## Phase 4: Expanded Creatures And Encounters

Goal: make creature data and encounter math useful for DM-facing tools.

Todo:

- Expand creature definitions with traits, bonus actions, reactions, resistances, vulnerabilities, immunities, and condition immunities.
- Add more SRD-style creatures.
- Add CR/XP helpers and party encounter difficulty calculations.
- Add encounter summary objects.

Done when:

- An encounter can summarize monsters, XP, adjusted difficulty, and basic combat-ready stats.

## Phase 5: Spells And Spellcasting

Goal: add spell definitions and spellcasting math without building the full
effect engine yet.

Todo:

- Add spell definitions: level, school, casting time, range, duration, components, concentration, ritual.
- Add spell attack bonus and spell save DC helpers.
- Add spell slot and pact magic state.
- Add basic spell effects for attack, save, damage, healing, and conditions.
- Add a small SRD-style spell catalog.

Done when:

- A spellcaster can make a spell attack, force a save, spend a slot, and apply simple damage/healing.

## Phase 6: Resources And Features

Goal: support class features and monster abilities that have limited uses.

Todo:

- Add a generic resource model for charges, short-rest uses, long-rest uses, proficiency-based uses, and recharge rolls.
- Add feature definitions and feature state.
- Add common feature examples such as Second Wind, Rage, Sneak Attack, Pack Tactics, and Recharge 5-6.

Done when:

- A feature can be used, depleted, restored, and demonstrated in tests.

## Phase 7: Effects And Conditions Runtime

Goal: make conditions, features, and spells affect mechanics in a reusable way.

Todo:

- Add structured effect/modifier objects.
- Add hooks for attack rolls, checks, saves, AC, damage, turn start, and turn end.
- Apply advantage/disadvantage from conditions.
- Add resistance, vulnerability, and immunity damage pipeline.
- Add concentration hooks.

Done when:

- Poisoned, restrained, prone, and unconscious have mechanical consequences in tests.

## Phase 8: Data Files And Content Pipeline

Goal: move scalable content out of Python constants.

Todo:

- Define JSON or YAML schemas for equipment, creatures, spells, classes, and features.
- Add loaders and validators.
- Keep built-in SRD content loadable as package data.
- Support user/homebrew content packs.

Done when:

- Built-in content is loaded through the same path a user content pack would use.

## Phase 9: Serialization And Validation

Goal: make the library useful for external tools and save files.

Todo:

- Add JSON serialization for characters, creatures, encounters, combat state, and resources.
- Add validation result objects with clear errors.
- Add import/export examples.

Done when:

- A character or encounter can round-trip through JSON with validation.

## Phase 10: Demo Tools

Goal: prove the library works in practical workflows.

Todo:

- Character builder CLI.
- Encounter runner CLI.
- Monster browser script.
- Spell lookup script.
- Combat simulation script.

Done when:

- A user can run small tools without writing Python code.

## Cross-Cutting Rules

- Keep mechanics and data separate where practical.
- Do not reproduce long-form copyrighted rule text.
- Prefer deterministic tests and demos.
- Add focused tests with every public API addition.
- Keep examples readable; they are both documentation and smoke tests.
- Update the runnable example and user-facing docs when public behavior changes.
