"""Tests for cep.utils – pure helper functions."""
from __future__ import annotations

import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from cep.utils import get_platform, parse_stdout, extract_archive, get_template_path


class TestParseStdout:
    def test_valid_json(self):
        data = {"key": "value", "nested": {"a": 1}}
        result = parse_stdout(json.dumps(data))
        assert result == data

    def test_json_with_whitespace_per_line(self):
        # Simulates nebula-cert output that has leading spaces per line
        raw = '  {\n  "details": {\n  "name": "host.net"\n  }\n  }'
        result = parse_stdout(raw)
        assert result["details"]["name"] == "host.net"

    def test_completely_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_stdout("this is not json at all !!!")


class TestGetPlatform:
    def test_returns_known_platform(self):
        platform = get_platform()
        assert platform in ("linux-amd64", "linux-arm64", "darwin-amd64", "darwin-arm64")


class TestExtractArchive:
    def test_extract_zip(self, tmp_path: Path):
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("hello.txt", "hello world")

        out_dir = tmp_path / "out"
        extract_archive(zip_path, "zip", out_dir)

        assert (out_dir / "hello.txt").read_text() == "hello world"

    def test_extract_tar_gz(self, tmp_path: Path):
        tar_path = tmp_path / "test.tar.gz"
        source = tmp_path / "hello.txt"
        source.write_text("hello tar")

        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(source, arcname="hello.txt")

        out_dir = tmp_path / "out"
        extract_archive(tar_path, "tar.gz", out_dir)

        assert (out_dir / "hello.txt").read_text() == "hello tar"

    def test_unsupported_type_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Unsupported archive type"):
            extract_archive(tmp_path / "f.rar", "rar", tmp_path / "out")


class TestGetTemplatePath:
    def test_bundle_json_exists(self):
        path = get_template_path("bundle.json")
        assert path is not None
        assert path.exists()

    def test_config_yml_exists(self):
        path = get_template_path("config.yml")
        assert path is not None
        assert path.exists()

    def test_nonexistent_returns_none(self):
        path = get_template_path("does_not_exist.yaml")
        assert path is None
