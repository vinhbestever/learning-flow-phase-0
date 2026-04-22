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


def list_students() -> list[int]:
    """Sorted list of student IDs that have student_context.json in output/."""
    result = []
    if _OUTPUT.exists():
        for child in sorted(_OUTPUT.iterdir()):
            if child.is_dir() and child.name.isdigit():
                if (child / "student_context.json").exists():
                    result.append(int(child.name))
    return result
