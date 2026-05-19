"""
Tests for cep.utils helpers.

TODO references:
  utils.py:54  – get_platform  "Just do linux"
  utils.py:71  – extract_archive
  utils.py:89  – download_nebula
  utils.py:115 – get_executable_path
  utils.py:139 – get_template_path
  utils.py:147 – parse_stdout

get_platform:
- linux-amd64 returned for x86_64
- linux-arm64 returned for aarch64

extract_archive:
- zip archives are extracted to target_dir
- tar.gz archives are extracted to target_dir
- unsupported type raises ValueError

download_nebula:
- skips download when nebula already exists
- downloads, extracts, makes executable, cleans up archive when missing

get_executable_path:
- raises ValueError for unknown names
- returns cached path when executable exists
- calls download_nebula when executable is missing

get_template_path:
- returns an existing Path for templates that ship with the package
- returns None for a name that doesn't exist in the package

parse_stdout:
- valid JSON string → dict
- JSON with surrounding whitespace/newlines → dict
- invalid JSON raises json.JSONDecodeError
"""
from __future__ import annotations

import json
import platform
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cep.utils import (
    extract_archive,
    get_executable_path,
    get_platform,
    get_template_path,
    parse_stdout,
)


# ---------------------------------------------------------------------------
# get_platform – only Linux variants tested per TODO ("Just do linux")
# ---------------------------------------------------------------------------

class TestGetPlatform:
    def test_linux_x86_64(self, monkeypatch):
        monkeypatch.setattr(platform, "machine", lambda: "x86_64")
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        assert get_platform() == "linux-amd64"

    def test_linux_amd64_alias(self, monkeypatch):
        monkeypatch.setattr(platform, "machine", lambda: "amd64")
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        assert get_platform() == "linux-amd64"

    def test_linux_aarch64(self, monkeypatch):
        monkeypatch.setattr(platform, "machine", lambda: "aarch64")
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        assert get_platform() == "linux-arm64"

    def test_linux_arm64_alias(self, monkeypatch):
        monkeypatch.setattr(platform, "machine", lambda: "arm64")
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        assert get_platform() == "linux-arm64"


# ---------------------------------------------------------------------------
# extract_archive
# ---------------------------------------------------------------------------

class TestExtractArchive:
    def test_extracts_zip(self, tmp_path):
        archive = tmp_path / "test.zip"
        payload = tmp_path / "hello.txt"
        payload.write_text("hello")

        with zipfile.ZipFile(archive, "w") as z:
            z.write(payload, arcname="hello.txt")

        out = tmp_path / "out"
        extract_archive(archive, "zip", out)

        assert (out / "hello.txt").read_text() == "hello"

    def test_extracts_tar_gz(self, tmp_path):
        archive = tmp_path / "test.tar.gz"
        payload = tmp_path / "world.txt"
        payload.write_text("world")

        with tarfile.open(archive, "w:gz") as tf:
            tf.add(payload, arcname="world.txt")

        out = tmp_path / "out"
        extract_archive(archive, "tar.gz", out)

        assert (out / "world.txt").read_text() == "world"

    def test_creates_target_dir(self, tmp_path):
        archive = tmp_path / "test.zip"
        with zipfile.ZipFile(archive, "w") as z:
            pass  # empty zip

        out = tmp_path / "deep" / "nested" / "dir"
        extract_archive(archive, "zip", out)

        assert out.is_dir()

    def test_unsupported_type_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Unsupported archive type"):
            extract_archive(tmp_path / "f.rar", "rar", tmp_path / "out")


# ---------------------------------------------------------------------------
# download_nebula
# ---------------------------------------------------------------------------

class TestDownloadNebula:
    def test_skips_download_when_nebula_exists(self, tmp_path, monkeypatch):
        """If CACHE_DIR/nebula already exists, urlretrieve must not be called."""
        nebula = tmp_path / "nebula"
        nebula.touch()

        monkeypatch.setattr("cep.utils.CACHE_DIR", tmp_path)
        monkeypatch.setattr(platform, "machine", lambda: "x86_64")
        monkeypatch.setattr(platform, "system", lambda: "Linux")

        with patch("cep.utils.urllib.request.urlretrieve") as mock_retrieve:
            from cep.utils import download_nebula
            download_nebula()

        mock_retrieve.assert_not_called()

    def test_downloads_and_extracts_when_missing(self, tmp_path, monkeypatch):
        """When nebula is absent, urlretrieve is called and archive is deleted afterward."""
        monkeypatch.setattr("cep.utils.CACHE_DIR", tmp_path)
        monkeypatch.setattr(platform, "machine", lambda: "x86_64")
        monkeypatch.setattr(platform, "system", lambda: "Linux")

        def fake_retrieve(url, dest):
            # linux-amd64 config uses tar.gz
            import io
            with tarfile.open(dest, "w:gz") as tf:
                for name in ("nebula", "nebula-cert"):
                    data = b"fake-binary"
                    info = tarfile.TarInfo(name=name)
                    info.size = len(data)
                    tf.addfile(info, io.BytesIO(data))

        with patch("cep.utils.urllib.request.urlretrieve", side_effect=fake_retrieve):
            from cep.utils import download_nebula
            download_nebula()

        assert not (tmp_path / "archive").exists(), "Archive must be cleaned up"

    def test_download_url_matches_linux_amd64(self, tmp_path, monkeypatch):
        """The URL passed to urlretrieve must match the linux-amd64 config."""
        monkeypatch.setattr("cep.utils.CACHE_DIR", tmp_path)
        monkeypatch.setattr(platform, "machine", lambda: "x86_64")
        monkeypatch.setattr(platform, "system", lambda: "Linux")

        captured_urls = []

        def fake_retrieve(url, dest):
            captured_urls.append(url)
            import io
            with tarfile.open(dest, "w:gz") as tf:
                for name in ("nebula", "nebula-cert"):
                    data = b"x"
                    info = tarfile.TarInfo(name=name)
                    info.size = len(data)
                    tf.addfile(info, io.BytesIO(data))

        with patch("cep.utils.urllib.request.urlretrieve", side_effect=fake_retrieve):
            from cep.utils import download_nebula
            download_nebula()

        assert len(captured_urls) == 1, "urlretrieve must be called exactly once"
        assert "linux-amd64" in captured_urls[0], f"Unexpected URL: {captured_urls[0]}"


# ---------------------------------------------------------------------------
# get_executable_path
# ---------------------------------------------------------------------------

class TestGetExecutablePath:
    def test_raises_for_unknown_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cep.utils.CACHE_DIR", tmp_path)
        with pytest.raises(ValueError, match="Unsupported executable"):
            get_executable_path("unknown-tool")

    def test_returns_path_when_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cep.utils.CACHE_DIR", tmp_path)
        (tmp_path / "nebula-cert").touch()

        with patch("cep.utils.download_nebula") as mock_dl:
            result = get_executable_path("nebula-cert")

        mock_dl.assert_not_called()
        assert result == tmp_path / "nebula-cert"

    def test_calls_download_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cep.utils.CACHE_DIR", tmp_path)

        def fake_download():
            (tmp_path / "nebula").touch()
            (tmp_path / "nebula-cert").touch()

        with patch("cep.utils.download_nebula", side_effect=fake_download):
            result = get_executable_path("nebula")

        assert result == tmp_path / "nebula"


# ---------------------------------------------------------------------------
# get_template_path
# ---------------------------------------------------------------------------

class TestGetTemplatePath:
    def test_returns_path_for_existing_template(self):
        """config.yml is a template that ships with the package."""
        result = get_template_path("config.yml")
        assert result is not None
        assert result.exists()

    def test_returns_none_for_missing_template(self):
        result = get_template_path("this_does_not_exist.conf")
        assert result is None


# ---------------------------------------------------------------------------
# parse_stdout
# ---------------------------------------------------------------------------

class TestParseStdout:
    def test_valid_json_string(self):
        assert parse_stdout('{"key": "value"}') == {"key": "value"}

    def test_json_with_surrounding_newlines(self):
        result = parse_stdout('\n  {"a": 1}  \n')
        assert result == {"a": 1}

    def test_json_with_internal_spaces_stripped(self):
        # Simulates output where OS adds spaces/newlines mid-JSON
        mangled = '{\n  "x": 2\n}'
        result = parse_stdout(mangled)
        assert result == {"x": 2}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_stdout("not json at all!!!")
