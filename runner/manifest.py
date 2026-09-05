"""
runner/manifest.py
Run Manifest Stub Generation and Management
Owner: Person B (Runtime & Platform Lead)
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RunManifest:
    """Represents a structured run manifest stub capturing execution metadata."""
    run_id: str
    instance_id: str
    repo_sha: str
    config_version: str = "w2-v1"
    runner_image: str = "repopilot-runner:w1"
    created_at: str = ""
    status: str = "initialized"

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write_json(self, target_path: Path | str) -> Path:
        """Serializes and writes the manifest stub to a JSON file."""
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunManifest:
        return cls(
            run_id=data["run_id"],
            instance_id=data["instance_id"],
            repo_sha=data["repo_sha"],
            config_version=data.get("config_version", "w2-v1"),
            runner_image=data.get("runner_image", "repopilot-runner:w1"),
            created_at=data.get("created_at", ""),
            status=data.get("status", "initialized"),
        )
