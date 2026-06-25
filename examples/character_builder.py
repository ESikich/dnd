from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

from dnd5e import (
    ARMOR,
    MAGIC_ITEMS,
    RACES,
    SHIELDS,
    SRD_CLASSES,
    SUBRACES,
    WEAPONS,
    Ability,
    CharacterClassName,
    CharacterClassLevel,
    CharacterLoadout,
    CharacterSheet,
    Skill,
    ability_modifier,
    character_sheet_armor_class,
    character_sheet_class_progression,
    character_sheet_hit_points,
    character_sheet_initiative_bonus,
    character_sheet_max_hit_points,
    character_sheet_passive_skill,
    character_sheet_saving_throw_bonus,
    character_sheet_skill_bonus,
    character_sheet_spellcasting_progression,
    character_sheet_to_data,
    character_sheet_weapon_profiles,
    proficiency_bonus,
    race_ability_bonuses,
    race_languages,
)
from dnd5e.skills import SKILL_ABILITIES

STATIC_DIR = Path(__file__).with_name("character_builder_static")
ABILITIES: tuple[Ability, ...] = ("str", "dex", "con", "int", "wis", "cha")
SKILLS: tuple[Skill, ...] = tuple(SKILL_ABILITIES)


def catalog_options() -> dict[str, Any]:
    """Return compact catalog data needed by the browser builder."""

    return {
        "abilities": list(ABILITIES),
        "skills": [
            {"id": skill, "ability": SKILL_ABILITIES[skill], "name": _title(skill)}
            for skill in SKILLS
        ],
        "races": [_dataclass_data(race) for race in sorted(RACES.values(), key=lambda item: item.name)],
        "subraces": [
            _dataclass_data(subrace)
            for subrace in sorted(SUBRACES.values(), key=lambda item: item.name)
        ],
        "classes": [
            _dataclass_data(class_definition)
            for class_definition in sorted(SRD_CLASSES.values(), key=lambda item: item.name)
        ],
        "armor": [_dataclass_data(item) for item in sorted(ARMOR.values(), key=lambda item: item.name)],
        "shields": [
            _dataclass_data(item) for item in sorted(SHIELDS.values(), key=lambda item: item.name)
        ],
        "weapons": [
            _dataclass_data(item) for item in sorted(WEAPONS.values(), key=lambda item: item.name)
        ],
        "magicItems": [
            _dataclass_data(item)
            for item in sorted(MAGIC_ITEMS.values(), key=lambda item: item.name)
            if not item.variant
        ],
    }


def build_character(payload: dict[str, Any]) -> dict[str, Any]:
    """Build and derive a character sheet from browser form data."""

    class_name = cast(CharacterClassName, str(payload.get("class", "fighter")))
    level = _int_value(payload.get("level"), 1)
    race_id = _optional_string(payload.get("race")) or "human"
    subrace_id = _optional_string(payload.get("subrace"))
    race = RACES[race_id]
    ability_choices = tuple(str(item) for item in payload.get("abilityChoices", []))
    if not ability_choices:
        ability_choices = tuple(
            option.ability for option in race.ability_bonus_options[: race.ability_bonus_choice_count]
        )
    language_choices = tuple(str(item) for item in payload.get("languageChoices", []))
    if not language_choices:
        language_choices = race.language_options[: race.language_choice_count]
    selected_skills = tuple(str(item) for item in payload.get("skills", []))
    class_definition = SRD_CLASSES[class_name]

    _validate_skill_choices(class_definition.skill_choices, class_definition.skill_choice_count, selected_skills)

    race_bonuses = race_ability_bonuses(
        race_id,
        subrace=subrace_id,
        ability_choices=ability_choices,  # type: ignore[arg-type]
    )
    base_abilities = _ability_scores(payload.get("abilities", {}))
    final_abilities: dict[Ability, int] = {
        ability: base_abilities[ability] + race_bonuses.get(ability, 0) for ability in ABILITIES
    }
    skill_proficiencies = {skill: "proficient" for skill in selected_skills}
    saving_throw_proficiencies = {
        ability: "proficient" for ability in class_definition.saving_throws
    }

    loadout = CharacterLoadout(
        armor=_optional_string(payload.get("armor")),
        shield=_optional_string(payload.get("shield")),
        weapons=tuple(str(item) for item in payload.get("weapons", [])),
        two_handed_weapons=tuple(str(item) for item in payload.get("twoHandedWeapons", [])),
        magic_items=tuple(str(item) for item in payload.get("magicItems", [])),
        attuned_magic_items=tuple(str(item) for item in payload.get("attunedMagicItems", [])),
    )
    maximum_hit_points = _optional_int(payload.get("maximumHitPoints"))
    current_hit_points = _optional_int(payload.get("currentHitPoints"))
    sheet = CharacterSheet(
        id=_slug(str(payload.get("name") or "hero")),
        name=str(payload.get("name") or "Hero"),
        classes=(CharacterClassLevel(class_name, level),),
        abilities=final_abilities,
        skill_proficiencies=skill_proficiencies,  # type: ignore[arg-type]
        saving_throw_proficiencies=saving_throw_proficiencies,  # type: ignore[arg-type]
        loadout=loadout,
        maximum_hit_points=maximum_hit_points,
        current_hit_points=current_hit_points,
        notes=tuple(str(item) for item in payload.get("notes", []) if str(item).strip()),
    )

    return character_summary(sheet, race_id, subrace_id, ability_choices, language_choices, base_abilities)


def character_summary(
    sheet: CharacterSheet,
    race_id: str,
    subrace_id: str | None,
    ability_choices: tuple[str, ...],
    language_choices: tuple[str, ...],
    base_abilities: dict[Ability, int],
) -> dict[str, Any]:
    hp = character_sheet_hit_points(sheet)
    ac = character_sheet_armor_class(sheet)
    race = RACES[race_id]
    subrace = SUBRACES[subrace_id] if subrace_id else None
    race_bonuses = race_ability_bonuses(
        race_id,
        subrace=subrace_id,
        ability_choices=ability_choices,  # type: ignore[arg-type]
    )

    return {
        "sheet": character_sheet_to_data(sheet),
        "lineage": {
            "race": _dataclass_data(race),
            "subrace": _dataclass_data(subrace) if subrace else None,
            "abilityBonuses": race_bonuses,
            "languages": list(race_languages(race_id, language_choices=language_choices)),
            "traits": list(dict.fromkeys((*race.traits, *((subrace.traits if subrace else ()))))),
        },
        "abilities": [
            {
                "id": ability,
                "name": ability.upper(),
                "base": base_abilities[ability],
                "bonus": race_bonuses.get(ability, 0),
                "score": sheet.abilities[ability],
                "modifier": ability_modifier(sheet.abilities[ability]),
            }
            for ability in ABILITIES
        ],
        "derived": {
            "level": sum(class_level.level for class_level in sheet.classes),
            "proficiencyBonus": proficiency_bonus(sum(class_level.level for class_level in sheet.classes)),
            "initiative": character_sheet_initiative_bonus(sheet),
            "armorClass": _dataclass_data(ac),
            "hitPoints": _dataclass_data(hp),
            "maximumHitPoints": character_sheet_max_hit_points(sheet),
            "savingThrows": [
                {
                    "id": ability,
                    "name": ability.upper(),
                    "bonus": character_sheet_saving_throw_bonus(sheet, ability),
                    "proficient": ability in sheet.saving_throw_proficiencies,
                }
                for ability in ABILITIES
            ],
            "skills": [
                {
                    "id": skill,
                    "name": _title(skill),
                    "ability": SKILL_ABILITIES[skill].upper(),
                    "bonus": character_sheet_skill_bonus(sheet, skill),
                    "passive": character_sheet_passive_skill(sheet, skill),
                    "proficient": skill in sheet.skill_proficiencies,
                }
                for skill in SKILLS
            ],
            "attacks": [_dataclass_data(profile) for profile in character_sheet_weapon_profiles(sheet)],
            "progression": _dataclass_data(character_sheet_class_progression(sheet)),
            "spellcasting": _dataclass_data(character_sheet_spellcasting_progression(sheet)),
        },
    }


class CharacterBuilderHandler(BaseHTTPRequestHandler):
    server_version = "DndCharacterBuilder/0.1"

    def do_GET(self) -> None:
        if self.path == "/api/options":
            self._send_json(catalog_options())
            return
        path = "/index.html" if self.path in ("/", "") else self.path
        self._send_static(path)

    def do_POST(self) -> None:
        if self.path != "/api/character":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("request body must be an object")
            self._send_json(build_character(payload))
        except (KeyError, TypeError, ValueError) as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, request_path: str) -> None:
        relative = Path(request_path.lstrip("/"))
        target = (STATIC_DIR / relative).resolve()
        if STATIC_DIR.resolve() not in target.parents and target != STATIC_DIR.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = {
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".html": "text/html; charset=utf-8",
        }.get(target.suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), CharacterBuilderHandler)
    print(f"Character builder running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping character builder.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the D&D 5E character builder web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    run(args.host, args.port)


def _dataclass_data(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)  # type: ignore[arg-type]
    return value


def _ability_scores(value: Any) -> dict[Ability, int]:
    scores = value if isinstance(value, dict) else {}
    return {ability: _int_value(scores.get(ability), 10) for ability in ABILITIES}


def _validate_skill_choices(
    allowed: tuple[Skill, ...],
    count: int,
    selected: tuple[str, ...],
) -> None:
    if len(selected) != count:
        raise ValueError(f"choose exactly {count} class skills")
    invalid = set(selected) - set(allowed)
    if invalid:
        raise ValueError(f"invalid class skill choices: {', '.join(sorted(invalid))}")


def _optional_string(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _optional_int(value: Any) -> int | None:
    return None if value in (None, "") else _int_value(value, 0)


def _int_value(value: Any, default: int) -> int:
    if value in (None, ""):
        return default
    return int(value)


def _slug(value: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "-" for character in value.strip())
    return "-".join(part for part in slug.split("-") if part) or "hero"


def _title(value: str) -> str:
    return value.replace("_", " ").title()


if __name__ == "__main__":
    main()
