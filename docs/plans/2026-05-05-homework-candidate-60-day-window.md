# (Superseded)

Implementation strategy changed after review.

**Use:** [2026-05-05-selector-pool-recency-window.md](./2026-05-05-selector-pool-recency-window.md)

**Summary:** Do **not** filter `scored_candidates` in preprocess. The diagnostic agent keeps the full tiered timeline; only the **selector question pool** in `build_context` applies the 60-day recency window.
