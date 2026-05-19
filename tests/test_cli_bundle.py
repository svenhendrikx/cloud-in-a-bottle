"""Tests for CepBundle – artifact generation (no network calls needed)."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from cep.cli.host import CepBundle


@pytest.fixture()
def bundle(dummy_nebula_files, tmp_path, monkeypatch) -> CepBundle:
    monkeypatch.chdir(tmp_path)
    return CepBundle(
        host_name="myhost",
        **{k: v for k, v in dummy_nebula_files.items() if k != "host_data"},
    )


class TestCepBundleMetadata:
    def test_generate_metadata_has_required_keys(self, bundle):
        meta = bundle.generate_metadata()
        assert meta["format"] == "cep-bundle"
        assert meta["format_version"] == 1
        assert "created_at" in meta
        assert meta["created_at"]  # non-empty

    def test_metadata_nebula_config_file(self, bundle):
        meta = bundle.generate_metadata()
        nebula = meta["backends"]["nebula"]
        assert nebula["config_file"] == bundle.config_out_path.name

    def test_metadata_nebula_files(self, bundle):
        meta = bundle.generate_metadata()
        files = meta["backends"]["nebula"]["files"]
        assert files["ca"] == bundle.ca_crt_path.name
        assert files["cert"] == bundle.crt_path.name
        assert files["key"] == bundle.priv_key_path.name


class TestCepBundleCreateArtifact:
    def test_artifact_is_created(self, bundle, tmp_path):
        path = bundle.create_artifact()
        assert path.exists()
        assert path.suffix == ".cepbundle"
        assert path.name == "myhost.cepbundle"

    def test_artifact_is_valid_zip(self, bundle):
        path = bundle.create_artifact()
        assert zipfile.is_zipfile(path)

    def test_artifact_contains_nebula_dir(self, bundle):
        path = bundle.create_artifact()
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        nebula_files = [n for n in names if n.startswith("nebula/")]
        assert nebula_files

    def test_artifact_contains_bundle_json(self, bundle):
        path = bundle.create_artifact()
        with zipfile.ZipFile(path) as zf:
            assert "bundle.json" in zf.namelist()
            meta = json.loads(zf.read("bundle.json"))
        assert meta["format"] == "cep-bundle"

    def test_artifact_contains_all_nebula_files(self, bundle):
        path = bundle.create_artifact()
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        expected = {
            f"nebula/{bundle.config_out_path.name}",
            f"nebula/{bundle.ca_crt_path.name}",
            f"nebula/{bundle.crt_path.name}",
            f"nebula/{bundle.priv_key_path.name}",
        }
        assert expected.issubset(names)

    def test_artifact_contents_match_source_files(self, bundle):
        path = bundle.create_artifact()
        with zipfile.ZipFile(path) as zf:
            key_content = zf.read(f"nebula/{bundle.priv_key_path.name}").decode()
        assert key_content == bundle.priv_key_path.read_text()
