from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path

from src.agents import AVAILABLE_AGENTS
from src.agents import base as base_module
from src.config import SUBMISSION_DIR


def package_agent_submission(agent_name: str, output_path: Path | str) -> Path:
    if agent_name not in AVAILABLE_AGENTS:
        raise ValueError(
            f"Unknown agent '{agent_name}'. Available: {list(AVAILABLE_AGENTS.keys())}"
        )

    agent_cls = AVAILABLE_AGENTS[agent_name]
    agent_module = inspect.getmodule(agent_cls)
    agent_source = inspect.getsource(agent_module) if agent_module else inspect.getsource(agent_cls)
    base_source = inspect.getsource(base_module)

    # Clean local package imports so my_agent.py is fully standalone
    cleaned_agent_source = agent_source.replace("from src.agents.base import BaseAgent", "").strip()

    adapter_code = f"""
try:
    from ..agent import Agent as OfficialAgent
except (ImportError, ValueError):
    try:
        from agents.agent import Agent as OfficialAgent
    except (ImportError, ValueError):
        OfficialAgent = object


class MyAgent(OfficialAgent):
    \"\"\"Adapter wrapping {agent_cls.__name__} for official ARC-AGI-3-Agents framework.\"\"\"
    MAX_ACTIONS = 400

    def __init__(self, *args, **kwargs):
        if OfficialAgent is not object:
            super().__init__(*args, **kwargs)
        self.inner_agent = {agent_cls.__name__}()

    def choose_action(self, frames, latest_frame):
        return self.inner_agent.choose_action(frames, latest_frame)

    def is_done(self, frames, latest_frame):
        return self.inner_agent.is_done(frames, latest_frame)

    def reset(self):
        self.inner_agent.reset()
"""

    combined_code = (
        "# --- BaseAgent Definition ---\n"
        + base_source
        + "\n\n# --- Agent Implementation ---\n"
        + cleaned_agent_source
        + "\n\n# --- Official Framework Adapter ---\n"
        + adapter_code
    )

    cell_0_wheels = (
        "!pip install --no-index --find-links \\\n"
        "    /kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels \\\n"
        "    arc-agi python-dotenv\n"
    )

    cell_1_agent = f"%%writefile /kaggle/working/my_agent.py\n{combined_code}\n"

    cell_2_rerun = """import os

if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
    # Wait for gateway to be ready
    !curl --fail --retry 999 --retry-all-errors --retry-delay 5 \\
          --retry-max-time 600 http://gateway:8001/api/games

    # Copy official framework to writable location
    !cp -r /kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents \\
           /kaggle/working/ARC-AGI-3-Agents

    # Copy custom agent into templates
    !cp /kaggle/working/my_agent.py \\
        /kaggle/working/ARC-AGI-3-Agents/agents/templates/my_agent.py

    # Minimal init with custom agent registration
    with open('/kaggle/working/ARC-AGI-3-Agents/agents/__init__.py', 'w') as f:
        f.write('''from typing import Type
from dotenv import load_dotenv
from .agent import Agent, Playback
from .swarm import Swarm
from .templates.random_agent import Random
from .templates.my_agent import MyAgent

load_dotenv()

AVAILABLE_AGENTS: dict[str, Type[Agent]] = {
    "random": Random,
    "myagent": MyAgent,
}
''')

    # Environment overrides for gateway
    with open('/kaggle/working/ARC-AGI-3-Agents/.env', 'w') as f:
        f.write('''SCHEME=http
HOST=gateway
PORT=8001
ARC_API_KEY=competition-key
ARC_BASE_URL=http://gateway:8001/
OPERATION_MODE=online
ENVIRONMENTS_DIR=
RECORDINGS_DIR=/kaggle/working/server_recording
''')

    # Run agent against all 110 games
    !cd /kaggle/working/ARC-AGI-3-Agents && \\
        MPLBACKEND=agg \\
        python main.py --agent myagent
"""

    cell_3_dummy = """import os
if not os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
    # Interactive / non-rerun commit mode dummy fallback
    import pandas as pd
    submission = pd.DataFrame(
        data=[['1_0', '1', True, 1]],
        columns=['row_id', 'game_id', 'end_of_game', 'score'])
    submission.to_parquet('/kaggle/working/submission.parquet', index=False)
    print("Dummy submission saved successfully for commit validation.")
"""

    notebook_dict = {
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
        "cells": [
            {
                "cell_type": "code",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": cell_0_wheels,
            },
            {
                "cell_type": "code",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": cell_1_agent,
            },
            {
                "cell_type": "code",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": cell_2_rerun,
            },
            {
                "cell_type": "code",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": cell_3_dummy,
            },
        ],
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(notebook_dict, f, indent=2)

    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Package ARC-AGI-3 Agent for Kaggle Submission")
    parser.add_argument(
        "--agent",
        choices=AVAILABLE_AGENTS.keys(),
        default="stochastic_goose",
        help="Agent name to package",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Target notebook destination path",
    )
    args = parser.parse_args()

    dest = Path(args.output) if args.output else SUBMISSION_DIR / f"submission_{args.agent}.ipynb"
    path = package_agent_submission(agent_name=args.agent, output_path=dest)
    print(f"✅ Packaged submission notebook generated at: {path}")


if __name__ == "__main__":
    main()
