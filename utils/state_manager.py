"""
State Manager - Persistent JSON state for pipeline resumability
"""
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StateManager:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return {}

    def save(self, data: dict):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def update(self, updates: dict):
        state = self.load()
        state.update(updates)
        self.save(state)

    def reset(self):
        if self.path.exists():
            self.path.unlink()
        logger.info(f"🗑️  State reset: {self.path}")
