# Agent Guide

This repository is a Python library for formalizing 5E-compatible D&D rules as
typed, mechanics-first APIs. Keep changes small, tested, and respectful of the
existing module style.

## Project Shape

- Source lives in `src/dnd5e`.
- Tests live in `tests`.
- The runnable showcase is `examples/exercise_library.py`.
- The phase roadmap is `ROADMAP.md`.
- Public API exports are centralized in `src/dnd5e/__init__.py`.

Current modules cover:

- Dice, d20 checks, abilities, proficiency, skills, saves
- Initiative, attack rolls, damage rolls
- Equipment, armor, weapons, AC, weapon profiles
- HP, healing, temporary HP, hit dice, rests, death saves
- Basic creature/stat block definitions
- Class metadata and condition metadata
- Combat runtime state with HP, AC, conditions, healing, and attack resolution
- Character sheets with class levels, loadouts, derived stats, HP, and combatants

## Development Rules

- Use Python 3.11+ syntax.
- Prefer immutable `@dataclass(frozen=True)` value objects for rules state.
- Prefer pure helper functions that return new state/result objects instead of
  mutating inputs.
- Keep public imports explicit in `src/dnd5e/__init__.py`.
- Add tests for every new public behavior.
- Update `examples/exercise_library.py` and relevant docs when public behavior
  changes or a feature is useful to demonstrate.
- Do not copy long-form rulebook prose. Model mechanics and metadata only.
- Use SRD-compatible content only unless the user explicitly supplies compatible
  homebrew content.
- Preserve existing public APIs unless a user explicitly asks for a breaking
  change.

## Commands

Run tests:

```sh
python3 -m pytest
```

Run lint and type checks:

```sh
ruff check .
pyright
```

Run the demo:

```sh
PYTHONPATH=src python3 examples/exercise_library.py
```

Install locally:

```sh
python3 -m pip install -e .
```

Install development tools:

```sh
python3 -m pip install -e ".[dev]"
```

## Implementation Pattern

For a new rules area:

1. Add narrow domain types in `types.py` only when they are shared across modules.
2. Add a focused module in `src/dnd5e`.
3. Export public symbols from `__init__.py`.
4. Add focused tests in `tests/test_<feature>.py`.
5. Update the demo and docs when they can show or explain the new behavior.
6. Run `ruff check .`, `pyright`, and `python3 -m pytest`.

## Preferred Next Work

Use `ROADMAP.md` as the source of truth for phase order, progress, and remaining
work. Do not treat a phase as complete while it still has any `Remaining` or
`Todo` items. Start with the first unfinished roadmap item, keep changes small,
and update `ROADMAP.md` whenever progress changes.
