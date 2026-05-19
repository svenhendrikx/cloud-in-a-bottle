"""
Tests for cep.apps.docker – ComposeConfig and Docker class methods.

DEPLOYMENT_PATH is patched per-test so nothing touches real user data dirs.
docker subprocesses are mocked.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

import cep.apps.docker as docker_module
from cep.apps.docker import ComposeConfig, Docker


@pytest.fixture(autouse=True)
def patch_deployment_path(tmp_path, monkeypatch):
    """Redirect DEPLOYMENT_PATH to a tmp file for every test in this module."""
    deployment_path = tmp_path / "compose.yml"
    monkeypatch.setattr(docker_module, "DEPLOYMENT_PATH", deployment_path)
    return deployment_path


# ---------------------------------------------------------------------------
# ComposeConfig
# ---------------------------------------------------------------------------


class TestComposeConfig:
    def test_load_nonexistent_returns_empty(self, tmp_path):
        cfg = ComposeConfig.load(tmp_path / "missing.yml")
        assert cfg.services == {}
        assert cfg.networks == {}

    def test_load_existing_file(self, tmp_path):
        data = {"services": {"nginx": {"image": "nginx:latest"}}}
        p = tmp_path / "compose.yml"
        p.write_text(yaml.safe_dump(data))

        cfg = ComposeConfig.load(p)
        assert "nginx" in cfg.services

    def test_save_and_reload(self, tmp_path):
        p = tmp_path / "compose.yml"
        cfg = ComposeConfig(services={"redis": {"image": "redis:7"}})
        cfg.save(p)

        restored = ComposeConfig.load(p)
        assert "redis" in restored.services

    def test_empty_file_returns_empty_config(self, tmp_path):
        p = tmp_path / "compose.yml"
        p.write_text("")
        cfg = ComposeConfig.load(p)
        assert cfg.services == {}


# ---------------------------------------------------------------------------
# Docker.list_available_apps
# ---------------------------------------------------------------------------


class TestDockerListAvailableApps:
    def test_returns_list_of_strings(self):
        apps = Docker.list_available_apps()
        assert isinstance(apps, list)
        assert len(apps) > 0
        assert all(isinstance(a, str) for a in apps)

    def test_known_templates_present(self):
        apps = Docker.list_available_apps()
        # Templates directory contains at least these files
        assert "nginx" in apps
        assert "redis" in apps


# ---------------------------------------------------------------------------
# Docker.get_app_template
# ---------------------------------------------------------------------------


class TestDockerGetAppTemplate:
    def test_known_template_returns_compose_config(self):
        cfg = Docker.get_app_template("nginx")
        assert isinstance(cfg, ComposeConfig)
        assert "nginx" in cfg.services

    def test_unknown_template_raises(self):
        with pytest.raises(ValueError, match="not found"):
            Docker.get_app_template("this_does_not_exist_xyz")


# ---------------------------------------------------------------------------
# Docker.add_to_deployment_file
# ---------------------------------------------------------------------------


class TestDockerAddToDeploymentFile:
    def test_adds_service_to_empty_file(self, tmp_path, patch_deployment_path):
        app_cfg = ComposeConfig(services={"redis": {"image": "redis:7"}})
        Docker.add_to_deployment_file(app_cfg)

        result = ComposeConfig.load(patch_deployment_path)
        assert "redis" in result.services

    def test_merges_two_apps(self, tmp_path, patch_deployment_path):
        Docker.add_to_deployment_file(ComposeConfig(services={"redis": {"image": "redis:7"}}))
        Docker.add_to_deployment_file(ComposeConfig(services={"nginx": {"image": "nginx:latest"}}))

        result = ComposeConfig.load(patch_deployment_path)
        assert "redis" in result.services
        assert "nginx" in result.services

    def test_overrides_existing_service(self, patch_deployment_path):
        Docker.add_to_deployment_file(ComposeConfig(services={"redis": {"image": "redis:6"}}))
        Docker.add_to_deployment_file(ComposeConfig(services={"redis": {"image": "redis:7"}}))

        result = ComposeConfig.load(patch_deployment_path)
        assert result.services["redis"]["image"] == "redis:7"


# ---------------------------------------------------------------------------
# Docker.update_deployment_file
# ---------------------------------------------------------------------------


class TestDockerUpdateDeploymentFile:
    def test_removes_service(self, patch_deployment_path):
        cfg = ComposeConfig(services={"redis": {}, "nginx": {}})
        cfg.save(patch_deployment_path)

        Docker.update_deployment_file("redis")

        result = ComposeConfig.load(patch_deployment_path)
        assert "redis" not in result.services
        assert "nginx" in result.services


# ---------------------------------------------------------------------------
# Docker.clear_deployment_file
# ---------------------------------------------------------------------------


class TestDockerClearDeploymentFile:
    def test_clears_all_services(self, patch_deployment_path):
        cfg = ComposeConfig(services={"redis": {}, "nginx": {}})
        cfg.save(patch_deployment_path)

        Docker.clear_deployment_file()

        result = ComposeConfig.load(patch_deployment_path)
        assert result.services == {}


# ---------------------------------------------------------------------------
# Docker.list_up
# ---------------------------------------------------------------------------


class TestDockerListUp:
    def test_empty_when_no_deployment(self, patch_deployment_path):
        assert Docker.list_up() == []

    def test_returns_service_names(self, patch_deployment_path):
        cfg = ComposeConfig(services={"redis": {}, "nginx": {}})
        cfg.save(patch_deployment_path)

        result = Docker.list_up()
        assert set(result) == {"redis", "nginx"}
