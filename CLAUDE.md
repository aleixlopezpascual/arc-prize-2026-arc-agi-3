# Claude Code Guidelines: ARC Prize 2026 - ARC-AGI-3

## Workflow & Verification
- Test all metric computations with `pytest tests/test_metrics.py`.
- Run offline agent evaluations against public environments in `input/environment_files/`.
- Ensure all code is cleanly formatted with `ruff check` and type-annotated.
- Document any agent runs and leaderboard metrics in `docs/experiments.md`.
