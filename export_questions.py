"""Backward-compatible CLI shim. Prefer: ``python -m scripts.export_questions`` from repo root."""

from scripts.export_questions import main

if __name__ == "__main__":
    main()
