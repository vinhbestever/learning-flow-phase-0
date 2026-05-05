"""Backward-compatible CLI shim. Prefer: ``python -m scripts.agent_pipeline`` from repo root."""

from scripts.agent_pipeline import main

if __name__ == "__main__":
    main()
