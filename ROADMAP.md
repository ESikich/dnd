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
- Equipment definition validation for impossible AC, costs, weights, damage, ranges, and metadata
- HP, healing, temporary HP, hit dice, rests, death saves
- Basic creature/stat block definitions for a growing SRD-style catalog
- Creature stat block validation for impossible HP, AC, ability scores, dice, movement, senses, and XP
- Creature metadata for traits, bonus actions, reactions, damage
  vulnerabilities/resistances/immunities, and condition immunities
- SRD-style class metadata with validation for impossible hit dice, proficiencies, and skill choices
- Condition metadata as validated tags
- Character sheets with class levels, loadouts, validation, derived HP, AC, skills, saves, attacks, and combatants
- HP state, hit dice pool, and death save state validation for impossible values
- Core character rules validation for impossible levels, missing or invalid ability scores, invalid proficiency choices, and invalid skill/save bonus keys
- A deterministic example program with a tiny battle
- Combat runtime state with validated HP, AC, conditions, healing, and attack action resolution
- Basic spell definitions with validated metadata and a small SRD-style catalog
- Basic spell-effect helpers for spell attacks, saving throw damage, healing, and conditions
- Effects runtime hooks for roll modifiers, AC modifiers, damage adjustment,
  start/end turn effects, and concentration checks

## Phase 1: Rules Foundation Polish

Goal: make the existing foundation consistent and dependable before adding
larger systems.

Status: Complete.

Progress:

- Done: naming consistency was reviewed across public modules; current public names are consistent enough to preserve without breaking changes before Phase 4.
- Done: character sheets validate loadout equipment IDs before derived AC or attack helpers run.
- Done: HP state, hit dice pool, and death save state objects validate impossible values at construction.
- Done: public HP dataclasses have docstrings describing their mechanics role.
- Done: `CharacterRules` validates level, ability score maps, proficiency choices, and skill/save bonus keys at construction.
- Done: creature actions and definitions validate impossible dice, HP, AC, ability scores, ranges, movement, senses, and XP at construction.
- Done: public creature dataclasses have docstrings describing their mechanics role.
- Done: public dice and d20 helper dataclasses/functions have docstrings describing their mechanics role.
- Done: equipment definitions validate impossible IDs, AC values, costs, weights, damage expressions, ranges, categories, damage types, and properties at construction.
- Done: public equipment dataclasses have docstrings describing their mechanics role.
- Done: class metadata validates impossible class names, hit dice, abilities, proficiencies, and skill choice counts at construction.
- Done: condition metadata validates condition names and mechanical tags at construction.
- Done: public class and condition dataclasses have docstrings describing their mechanics role.
- Done: combat runtime dataclasses validate impossible combatants, combat state order, attack outcomes, and damage results at construction.
- Done: public combat runtime dataclasses have docstrings describing their mechanics role.
- Done: public character rules and sheet dataclasses/functions have docstrings describing their mechanics role.
- Done: public combat, creature, equipment, and HP helper functions have docstrings describing their mechanics role.
- Done: README examples show current character-sheet and creature combatant helpers.
- Done: README documents test, demo, and `ruff` quality commands.
- Done: `mypy` is deferred until public typing shapes settle further.
- Done: dice notation and d20 input validation paths are covered by focused tests.

Done criteria:

- Done: existing modules are documented and tested.
- Done: the README accurately reflects the current API.
- Done: `python3 -m pytest` passes.

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

Status: Complete.

Progress:

- Done: expand creature definitions with named trait, bonus action, and reaction metadata.
- Done: add creature damage vulnerability, resistance, immunity, and condition
  immunity metadata with validation.
- Done: add another SRD-style creature entry to exercise creature metadata.
- Done: add CR/XP helpers, party encounter thresholds, adjusted XP, and summary
  objects.
- Done: add bandit, zombie, and ogre SRD-style creature entries to broaden
  humanoid, undead, and higher-CR encounter coverage.
- Done: add kobold, orc, axe beak, bugbear, and ghoul SRD-style creature
  entries to broaden low- and mid-CR encounter coverage.
- Done: add black bear, giant spider, and gray ooze SRD-style creature entries
  to broaden beast, ooze, trait, resistance, and condition-immunity coverage.
- Done: the representative SRD-style creature catalog is broad enough for this
  phase; further catalog growth is ongoing content work rather than a blocker.

Done when:

- Done: an encounter can summarize monsters, XP, adjusted difficulty, and basic combat-ready stats.

## Phase 5: Spells And Spellcasting

Goal: add spell definitions and spellcasting math without building the full
effect engine yet.

Status: Complete.

Progress:

- Done: add spell definitions for level, school, casting time, range, duration,
  components, concentration, and ritual metadata.
- Done: add a small SRD-style spell catalog.
- Done: add spell attack bonus and spell save DC helpers for character rules
  and character sheets.
- Done: add spell slot and pact magic runtime state with spend and restore
  helpers.
- Done: add basic spell-effect helpers for spell attacks, saving throw damage,
  rolled healing, and condition application.

Deferred:

- Rich spell area targeting, concentration, scaling, ongoing effects, and
  resistance/immunity integration wait for the effects runtime phases.

Done when:

- Done: a spellcaster can make a spell attack, force a save, spend a slot, and
  apply simple damage/healing.

## Phase 6: Resources And Features

Goal: support class features and monster abilities that have limited uses.

Status: Complete.

Progress:

- Done: add a generic resource model for charges, short-rest uses, long-rest
  uses, proficiency-based uses, and recharge rolls.
- Done: add feature definitions and runtime feature state.
- Done: add common feature examples for Second Wind, Rage, Sneak Attack, Pack
  Tactics, proficiency-based uses, and Recharge 5-6.
- Done: add focused helpers for Second Wind healing and Sneak Attack bonus
  damage dice/rolls.
- Done: connect creature recharge metadata to rechargeable creature action
  definitions and runtime feature/resource state.

Done when:

- Done: a feature can be used, depleted, restored, and demonstrated in tests.

## Phase 7: Effects And Conditions Runtime

Goal: make conditions, features, and spells affect mechanics in a reusable way.

Status: Complete.

Todo:

- Done: add structured roll modifier and damage adjustment result objects.
- Done: add condition hooks for attack rolls, ability checks, saving throws,
  action prevention, nearby forced critical hits, and condition immunity.
- Done: apply advantage/disadvantage from poisoned, restrained, prone, and
  unconscious conditions in focused runtime helpers.
- Done: add resistance, vulnerability, and immunity damage pipeline using
  creature source metadata.
- Done: add AC, turn start, and turn end effect hooks.
- Done: add concentration save DC and check hooks for damage-triggered concentration saves.

Done when:

- Done: poisoned, restrained, prone, and unconscious have mechanical consequences in tests.
- Done: AC modifiers and start/end turn effects have mechanical consequences
  in tests.
- Done: concentration checks have mechanical consequences in tests.

## Phase 8: Data Files And Content Pipeline

Goal: move scalable content out of Python constants.

Progress:

- Done: add JSON equipment content-pack schema checks and loaders for packaged
  and user-provided armor, shield, and weapon data.
- Done: load built-in armor, shield, and weapon catalogs through the same
  equipment content-pack path exposed to users.

Todo:

- Define JSON or YAML schemas for creatures, spells, classes, and features.
- Add loaders and validators for creatures, spells, classes, and features.
- Keep remaining built-in SRD content loadable as package data.
- Broaden user/homebrew content pack support beyond equipment.

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
