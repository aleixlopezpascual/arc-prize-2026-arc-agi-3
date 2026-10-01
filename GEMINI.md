# Gemini CLI Assistant Guidelines: ARC Prize 2026 - ARC-AGI-3

## Core Mandates
1. **Always Verify Locally:** Before recommending or generating submission notebooks, verify the agent logic on public games in `input/environment_files/` and score using `src/metrics.py`.
2. **Respect the Efficiency Penalty:** Because action efficiency is squared, avoid exhaustive random walks; prioritize goal hypothesis generation, connected-component tracking, and search pruning.
3. **Execution Budget:** Keep in mind the competition rerun constraint of ~4.9 minutes per game across 110 private games.
4. **Follow Directory Contracts:**
   - Agent logic goes in `src/agents/`.
   - Evaluation metrics in `src/metrics.py`.
   - Log experiment results in `docs/experiments.md`.
