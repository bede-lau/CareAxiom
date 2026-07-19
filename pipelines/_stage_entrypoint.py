from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_stage(stage_number: int) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    command = [
        sys.executable,
        str(repo_root / "scripts" / "run_pipeline.py"),
        str(stage_number),
        *sys.argv[1:],
    ]
    return subprocess.call(command, cwd=repo_root)
