"""Backward-compatible CLI shim. Prefer: ``python -m scripts.preprocess`` from repo root."""

from scripts.preprocess import main

if __name__ == "__main__":
    main()
