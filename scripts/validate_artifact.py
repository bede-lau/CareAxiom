from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the packaged Databricks App artifact.")
    parser.add_argument(
        "artifact",
        nargs="?",
        type=Path,
        default=REPO_ROOT / ".dist" / "react-app",
    )
    return parser.parse_args()


def main() -> int:
    artifact = parse_args().artifact.resolve()
    required = [
        artifact / "app.yaml",
        artifact / "pyproject.toml",
        artifact / "uv.lock",
        artifact / "src" / "medical_desert" / "api" / "main.py",
        artifact / "src" / "medical_desert" / "presentation" / "static" / "index.html",
        artifact / "artifact-manifest.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing artifact files:\n" + "\n".join(missing))
    prohibited = [
        artifact / "frontend",
        artifact / "tests",
        artifact / ".env",
        artifact / "package.json",
        artifact / "package-lock.json",
    ]
    present = [str(path) for path in prohibited if path.exists()]
    if present:
        raise ValueError("Prohibited artifact paths:\n" + "\n".join(present))

    app_config = yaml.safe_load((artifact / "app.yaml").read_text(encoding="utf-8"))
    if app_config.get("command") != ["python", "-m", "medical_desert.api.main"]:
        raise ValueError("app.yaml does not start the FastAPI production module")

    manifest_path = artifact / "artifact-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_paths = {entry["path"] for entry in manifest["files"]}
    expected_paths.add("artifact-manifest.json")
    actual_paths = {
        path.relative_to(artifact).as_posix()
        for path in artifact.rglob("*")
        if path.is_file()
    }
    unexpected = sorted(actual_paths - expected_paths)
    missing_manifest_files = sorted(expected_paths - actual_paths)
    if unexpected or missing_manifest_files:
        raise ValueError(
            "Artifact file set differs from manifest: "
            f"unexpected={unexpected}, missing={missing_manifest_files}"
        )
    for entry in manifest["files"]:
        path = artifact / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            raise ValueError(f"Artifact hash mismatch: {entry['path']}")

    text_extensions = {".py", ".yaml", ".yml", ".toml", ".json", ".js", ".css", ".html"}
    secret_markers = ("dapi", "TAVILY_API_KEY=", "client_secret")
    for path in artifact.rglob("*"):
        if path.is_file() and path.suffix.lower() in text_extensions:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(marker in text for marker in secret_markers):
                raise ValueError(f"Potential secret material in {path.relative_to(artifact)}")

    print(
        json.dumps(
            {
                "artifact": str(artifact),
                "status": "valid",
                "file_count": len(manifest["files"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
