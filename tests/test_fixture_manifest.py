from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.oracles import file_sha256


@pytest.mark.contract
@pytest.mark.gate("G0")
def test_fixture_manifest_hashes_every_declared_file(repo_root: Path) -> None:
    manifest = repo_root / "fixtures" / "manifest.sha256"
    entries = [
        line.split(maxsplit=1)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert entries
    for expected_hash, relative_path in entries:
        path = repo_root / relative_path
        assert path.is_file(), relative_path
        assert file_sha256(path) == expected_hash


@pytest.mark.contract
@pytest.mark.gate("G0")
def test_fixture_manifest_covers_all_json_fixtures(repo_root: Path) -> None:
    declared = {
        line.split(maxsplit=1)[1]
        for line in (repo_root / "fixtures" / "manifest.sha256")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    actual = {
        path.relative_to(repo_root).as_posix()
        for path in (repo_root / "fixtures").rglob("*.json")
    }
    assert declared == actual
