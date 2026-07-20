#!/usr/bin/env python3
"""Tests for batch export manager helpers."""

from pathlib import Path

from scenefab.services.export.batch_export_manager import BatchExportManager
from scenefab.utils.json_io import write_json


def test_load_project_data_from_json_file(tmp_path: Path):
    project_file = tmp_path / "project.json"
    write_json(project_file, {"name": "json-file"})

    data = BatchExportManager._load_project_data(str(project_file))

    assert data["name"] == "json-file"


def test_load_project_data_from_project_directory(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    write_json(project_dir / "project.json", {"name": "project-dir"})

    data = BatchExportManager._load_project_data(str(project_dir))

    assert data["name"] == "project-dir"


def test_load_project_data_falls_back_to_source_path(tmp_path: Path):
    source_path = tmp_path / "video.mp4"

    data = BatchExportManager._load_project_data(str(source_path))

    assert data == {"source": str(source_path)}
