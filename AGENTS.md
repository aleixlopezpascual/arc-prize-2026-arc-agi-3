# Repository Guidelines: ARC Prize 2026 - ARC-AGI-3

## 1. Project Purpose & Scope
This repository contains competitive agent implementations, evaluation harness code, and submission pipelines for Kaggle's **ARC Prize 2026 - ARC-AGI-3** competition (`arc-prize-2026-arc-agi-3`).

---

## 2. Code Standards & Tooling
- **Language & Runtime:** Python >= 3.10.
- **Typing & Documentation:** Strict type annotations on all public functions/methods. Clear docstrings explaining action selection rationale.
- **Linting & Formatting:** Follow Ruff standards with max line length 100.
- **Testing:** Pytest for all metric calculations, agent interfaces, and state transformation utilities.
  - Run tests: `pytest tests/`

---

## 3. Local Validation Gate
- **Never submit unverified agents to Kaggle.**
- Always run local evaluation against the 25 public games (`input/environment_files/`) using `src/metrics.py`.
- Any PR or model iteration must demonstrate a score improvement or actionable behavioral insight logged in `docs/experiments.md`.

---

## 4. Artifact Contracts & Directory Layout
- `src/`: Core agent algorithms, environment wrappers, perception modules, and metrics.
  - `src/config.py`: Directory paths and runtime configuration.
  - `src/metrics.py`: Official competition metric calculation.
  - `src/agents/`: Agent implementations inheriting from standard Agent base class.
- `input/`: Raw datasets, wheels, and public environment definitions.
- `notebooks/`: Public baselines, exploration, and submission development notebooks.
- `docs/`: Competition intel, briefs, and experiment tracking ledger (`docs/experiments.md`).
- `submissions/`: Bundled submission scripts and notebooks.
- `tests/`: Automated unit and integration tests.

---

## 5. Metric Anchor
$$\text{Level Score} = \min\left(100.0, \left(\frac{\text{baseline\_actions}}{\text{agent\_actions}}\right)^2 \times 100.0\right) \quad (\text{if level completed, else } 0.0)$$
$$\text{Game Score} = \frac{\sum_{i=1}^L i \cdot s_i}{\sum_{i=1}^L i}$$
$$\text{Total Score} = \frac{1}{N} \sum_{g=1}^N \text{Game Score}_g \in [0\%, 100\%]$$
Quadratic penalty on action inefficiency makes random walking costly; search must be targeted and hypothesis-driven.
