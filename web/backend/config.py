from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
_OUTPUT = _ROOT / "output"


def student_paths(student_id: int | str) -> dict[str, Path]:
    d = _OUTPUT / str(student_id)
    return {
        "context": d / "student_context.json",
        "questions": d / "questions_export.json",
        "homework": d / "homework_assignment.json",
        "diagnostic": d / "diagnostic_output.txt",
    }


def list_students() -> list[str]:
    """Sorted folder names under output/ that contain student_context.json.

    Names may be numeric (e.g. ``2102555``) or composite (e.g. ``2111414_newstudent``).
    """
    result: list[str] = []
    if not _OUTPUT.exists():
        return result
    for child in sorted(_OUTPUT.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith("."):
            continue
        if (child / "student_context.json").exists():
            result.append(name)
    return result
