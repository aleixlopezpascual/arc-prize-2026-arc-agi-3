from __future__ import annotations

import random
from collections.abc import Sequence

import numpy as np
import torch
import torch.nn.functional as F
from arcengine import FrameData, GameAction
from torch import nn

from src.agents.base import BaseAgent


class PolicyCNN(nn.Module):
    """Compact ConvNet mapping grid observations (16 colors) to action distributions."""

    def __init__(self, num_actions: int = 7) -> None:
        super().__init__()
        # Input: 16 channels (one-hot color states 0-15) over 64x64 grid
        self.conv1 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1)  # 32x32
        self.conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=2, padding=1)  # 16x16
        self.pool = nn.AdaptiveAvgPool2d((4, 4))
        self.fc = nn.Linear(64 * 4 * 4, num_actions)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = F.relu(self.conv1(x))
        h = F.relu(self.conv2(h))
        h = F.relu(self.conv3(h))
        h = self.pool(h)
        h = h.view(h.size(0), -1)
        return self.fc(h)


class StochasticGoose(BaseAgent):
    """Tufa Labs Milestone 1 CNN action learner."""

    def __init__(self, epsilon: float = 0.2, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self.epsilon = epsilon
        self.device = torch.device(
            "mps"
            if torch.backends.mps.is_available()
            else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.policy = PolicyCNN(num_actions=7).to(self.device)
        self.policy.eval()

    def _encode_grid(self, frame: FrameData) -> torch.Tensor:
        grid = np.zeros((64, 64), dtype=np.int64)
        if frame.frame and len(frame.frame) > 0:
            raw = frame.frame[0]
            if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], list):
                h = min(len(raw), 64)
                w = min(len(raw[0]), 64)
                grid[:h, :w] = np.array(raw)[:h, :w]

        # One-hot encode 16 color channels: shape (1, 16, 64, 64)
        tensor_grid = torch.from_numpy(grid).long()
        one_hot = F.one_hot(tensor_grid, num_classes=16).permute(2, 0, 1).unsqueeze(0).float()
        return one_hot.to(self.device)

    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction:
        # Filter out ACTION6 temporarily
        available = [a for a in latest_frame.available_actions if a != 6]
        if not available:
            return GameAction.RESET

        # Epsilon-greedy exploration
        if self.rng.random() < self.epsilon:
            action_int = self.rng.choice(available)
        else:
            with torch.no_grad():
                x = self._encode_grid(latest_frame)
                logits = self.policy(x).squeeze(0).cpu().numpy()

                # Mask unavailable actions
                masked_logits = np.full_like(logits, -1e9)
                for act_id in available:
                    idx = act_id - 1
                    if 0 <= idx < len(logits):
                        masked_logits[idx] = logits[idx]

                action_int = int(np.argmax(masked_logits)) + 1

        action = GameAction.from_id(action_int)
        # if action == GameAction.ACTION6:
        #    ...
        return action
