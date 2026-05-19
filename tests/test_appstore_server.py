"""
Tests for cep.apps.main – the appstore FastAPI server.

Docker class methods and subprocess calls are mocked so no real
Docker daemon is required.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cep.apps.main import app


@pytest.fixture()
def client():
    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == "ok"


class TestStoreHealth:
    def test_store_health_returns_ok(self, client):
        resp = client.get("/store/health")
        assert resp.status_code == 200
        assert resp.json() == "ok"


class TestListUp:
    def test_list_returns_service_names(self, client):
        with patch("cep.apps.main.Docker.list_up", return_value=["redis", "nginx"]):
            resp = client.get("/list")
        assert resp.status_code == 200
        assert set(resp.json()) == {"redis", "nginx"}

    def test_list_empty(self, client):
        with patch("cep.apps.main.Docker.list_up", return_value=[]):
            resp = client.get("/list")
        assert resp.status_code == 200
        assert resp.json() == []


class TestStoreList:
    def test_store_list_returns_available_apps(self, client):
        with patch("cep.apps.store.Docker.list_available_apps", return_value=["nginx", "redis"]):
            resp = client.get("/store/list")
        assert resp.status_code == 200
        apps = resp.json()
        assert "nginx" in apps


class TestDeploy:
    def test_deploy_calls_docker_methods(self, client):
        fake_cfg = MagicMock()
        with patch("cep.apps.main.Docker.get_app_template", return_value=fake_cfg) as mock_get, \
             patch("cep.apps.main.Docker.add_to_deployment_file") as mock_add, \
             patch("cep.apps.main.Docker.compose_up") as mock_up:
            resp = client.post("/deploy", params={"name": "nginx"})

        mock_get.assert_called_once_with("nginx")
        mock_add.assert_called_once_with(fake_cfg)
        mock_up.assert_called_once()


class TestTargetedDestroy:
    def test_destroy_updates_deployment_on_success(self, client):
        with patch("cep.apps.main.Docker.targeted_destroy", new_callable=AsyncMock, return_value=0) as mock_destroy, \
             patch("cep.apps.main.Docker.update_deployment_file") as mock_update:
            resp = client.delete("/targetedDestroy", params={"name": "redis"})

        mock_destroy.assert_called_once_with("redis")
        mock_update.assert_called_once_with("redis")

    def test_destroy_skips_update_on_failure(self, client):
        with patch("cep.apps.main.Docker.targeted_destroy", new_callable=AsyncMock, return_value=1), \
             patch("cep.apps.main.Docker.update_deployment_file") as mock_update:
            client.delete("/targetedDestroy", params={"name": "redis"})

        mock_update.assert_not_called()


class TestClear:
    def test_clear_clears_deployment_on_success(self, client):
        with patch("cep.apps.main.Docker.clear", new_callable=AsyncMock, return_value=0), \
             patch("cep.apps.main.Docker.clear_deployment_file") as mock_clear:
            resp = client.delete("/clear")

        mock_clear.assert_called_once()

    def test_clear_skips_on_failure(self, client):
        with patch("cep.apps.main.Docker.clear", new_callable=AsyncMock, return_value=1), \
             patch("cep.apps.main.Docker.clear_deployment_file") as mock_clear:
            client.delete("/clear")

        mock_clear.assert_not_called()
