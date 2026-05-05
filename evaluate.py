"""Backward-compatible CLI shim. Prefer: ``python -m scripts.evaluate`` from repo root."""

from scripts.evaluate import main

if __name__ == "__main__":
    main()
