from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / ".dist" / "react-app"
STATIC_ROOT = REPO_ROOT / "src" / "medical_desert" / "presentation" / "static"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the exact Databricks React App artifact.")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--output", type=Path, default=DIST_ROOT)
    return parser.parse_args()


def run(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def resolve_npm_executable(platform_name: str | None = None) -> str:
    platform_name = platform_name or os.name
    candidates = ("npm.cmd", "npm.exe") if platform_name == "nt" else ("npm",)
    for candidate in candidates:
        executable = shutil.which(candidate)
        if executable:
            return executable

    if platform_name == "nt":
        for environment_name in ("ProgramFiles", "ProgramFiles(x86)"):
            program_files = os.environ.get(environment_name)
            if not program_files:
                continue
            fallback_executable = Path(program_files) / "nodejs" / "npm.cmd"
            if fallback_executable.is_file():
                return str(fallback_executable)

    raise FileNotFoundError(
        "npm was not found. Install Node.js or add its installation directory to PATH."
    )


def copy_required(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Required package input does not exist: {source}")
    if source.is_dir():
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def file_manifest(root: Path) -> list[dict[str, str | int]]:
    entries: list[dict[str, str | int]] = []
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        content = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return entries


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    expected_parent = (REPO_ROOT / ".dist").resolve()
    if expected_parent not in output.parents:
        raise ValueError(f"Artifact output must remain under {expected_parent}")

    if output.exists():
        shutil.rmtree(output)

    if not args.skip_build:
        lockfile = REPO_ROOT / "package-lock.json"
        if not lockfile.exists():
            raise FileNotFoundError(
                "package-lock.json is required for the reproducible frontend build"
            )
        npm = resolve_npm_executable()
        run([npm, "ci"])
        run([npm, "run", "build"])
    if not (STATIC_ROOT / "index.html").exists():
        raise FileNotFoundError("Frontend build did not produce presentation/static/index.html")

    output.mkdir(parents=True)

    for relative in (
        "app.yaml",
        "pyproject.toml",
        "uv.lock",
        "src/medical_desert",
        "config",
        "artifacts/data-contracts",
        "sql/lakebase_schema.sql",
    ):
        copy_required(REPO_ROOT / relative, output / relative)

    manifest = {
        "artifact": "react-app",
        "entrypoint": "python -m medical_desert.api.main",
        "frontend_output": "src/medical_desert/presentation/static",
        "files": file_manifest(output),
    }
    (output / "artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
