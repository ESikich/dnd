from __future__ import annotations

import runpy
from pathlib import Path


def test_exercise_library_example_runs(capsys) -> None:
    example = Path(__file__).parents[1] / "examples" / "exercise_library.py"

    runpy.run_path(str(example), run_name="__main__")

    output = capsys.readouterr().out
    assert "D&D 5E Rules Library Demo" in output
    assert "Core Math" in output
    assert "Combat" in output
    assert "A Tiny Battle" in output
    assert "Result: Kara wins." in output
    assert "Rest And Recovery" in output
