"""
Tests for the storage CLI sub-commands (pool and volume).

All HTTP calls are mocked so no real server is needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cep.cli.main import app


@pytest.fixture()
def runner():
    return CliRunner()


def _ok(json_data=None):
    mock = MagicMock()
    mock.status_code = 200
    mock.raise_for_status.return_value = None
    mock.json.return_value = json_data if json_data is not None else {}
    return mock


def _err(status_code: int = 404, detail: str = "not found"):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {"detail": detail}
    mock.text = detail
    return mock


# ---------------------------------------------------------------------------
# storage pool
# ---------------------------------------------------------------------------


class TestStoragePoolCreate:
    def test_create_success_prints_confirmation(self, runner):
        with patch("cep.cli.storage.pool.client") as mock_client:
            mock_client.post.return_value = _ok({"name": "mypool"})
            result = runner.invoke(app, ["storage", "pool", "create", "mypool"])
        assert result.exit_code == 0
        assert "mypool" in result.output
        mock_client.post.assert_called_once_with("/create", params={"name": "mypool"})

    def test_create_error_prints_detail(self, runner):
        with patch("cep.cli.storage.pool.client") as mock_client:
            mock_client.post.return_value = _err(409, "Pool 'mypool' already exists")
            result = runner.invoke(app, ["storage", "pool", "create", "mypool"])
        assert result.exit_code == 0  # CLI handles errors gracefully (no raise_for_status)
        assert "already exists" in result.output


class TestStoragePoolDelete:
    def test_delete_success(self, runner):
        with patch("cep.cli.storage.pool.client") as mock_client:
            mock_client.delete.return_value = _ok({"status": "deleted"})
            result = runner.invoke(app, ["storage", "pool", "delete", "mypool"])
        assert result.exit_code == 0
        assert "mypool" in result.output
        mock_client.delete.assert_called_once_with("/delete", params={"name": "mypool"})

    def test_delete_not_found(self, runner):
        with patch("cep.cli.storage.pool.client") as mock_client:
            mock_client.delete.return_value = _err(404, "does not exist")
            result = runner.invoke(app, ["storage", "pool", "delete", "ghost"])
        assert result.exit_code == 0
        assert "does not exist" in result.output


class TestStoragePoolList:
    def test_list_with_pools(self, runner):
        pools = [
            {"name": "pool1", "volume_count": 2, "total_size_bytes": 1024},
            {"name": "pool2", "volume_count": 0, "total_size_bytes": 0},
        ]
        with patch("cep.cli.storage.pool.client") as mock_client:
            mock_client.get.return_value = _ok(pools)
            result = runner.invoke(app, ["storage", "pool", "list"])
        assert result.exit_code == 0
        assert "pool1" in result.output
        assert "pool2" in result.output

    def test_list_empty(self, runner):
        with patch("cep.cli.storage.pool.client") as mock_client:
            mock_client.get.return_value = _ok([])
            result = runner.invoke(app, ["storage", "pool", "list"])
        assert result.exit_code == 0
        assert "No pools" in result.output


class TestStoragePoolShow:
    def test_show_prints_details(self, runner):
        stats = {
            "name": "pool1",
            "path": "/pools/pool1",
            "volume_count": 3,
            "total_size_bytes": 4096,
            "created_at": "2025-01-01T00:00:00+00:00",
        }
        with patch("cep.cli.storage.pool.client") as mock_client:
            mock_client.get.return_value = _ok(stats)
            result = runner.invoke(app, ["storage", "pool", "show", "pool1"])
        assert result.exit_code == 0
        assert "pool1" in result.output
        assert "4096" in result.output

    def test_show_not_found(self, runner):
        with patch("cep.cli.storage.pool.client") as mock_client:
            mock_client.get.return_value = _err(404, "does not exist")
            result = runner.invoke(app, ["storage", "pool", "show", "ghost"])
        assert result.exit_code == 0
        assert "does not exist" in result.output


# ---------------------------------------------------------------------------
# storage volume
# ---------------------------------------------------------------------------


class TestStorageVolumeCreate:
    def test_create_success(self, runner):
        with patch("cep.cli.storage.volume.client") as mock_client:
            mock_client.post.return_value = _ok({"name": "vol1", "pool_name": "pool1"})
            result = runner.invoke(app, ["storage", "volume", "create", "pool1", "vol1"])
        assert result.exit_code == 0
        assert "vol1" in result.output
        mock_client.post.assert_called_once_with("/create", params={"pool_name": "pool1", "name": "vol1"})

    def test_create_duplicate_shows_error(self, runner):
        with patch("cep.cli.storage.volume.client") as mock_client:
            mock_client.post.return_value = _err(409, "already exists")
            result = runner.invoke(app, ["storage", "volume", "create", "pool1", "vol1"])
        assert result.exit_code == 0
        assert "already exists" in result.output


class TestStorageVolumeDelete:
    def test_delete_success(self, runner):
        with patch("cep.cli.storage.volume.client") as mock_client:
            mock_client.delete.return_value = _ok({"status": "deleted"})
            result = runner.invoke(app, ["storage", "volume", "delete", "pool1", "vol1"])
        assert result.exit_code == 0
        assert "vol1" in result.output
        mock_client.delete.assert_called_once_with("/delete", params={"pool_name": "pool1", "name": "vol1"})

    def test_delete_not_found(self, runner):
        with patch("cep.cli.storage.volume.client") as mock_client:
            mock_client.delete.return_value = _err(404, "does not exist")
            result = runner.invoke(app, ["storage", "volume", "delete", "pool1", "ghost"])
        assert result.exit_code == 0
        assert "does not exist" in result.output


class TestStorageVolumeList:
    def test_list_all_volumes(self, runner):
        volumes = [
            {"name": "v1", "pool_name": "pool1", "host_path": "/pools/pool1/v1"},
            {"name": "v2", "pool_name": "pool1", "host_path": "/pools/pool1/v2"},
        ]
        with patch("cep.cli.storage.volume.client") as mock_client:
            mock_client.get.return_value = _ok(volumes)
            result = runner.invoke(app, ["storage", "volume", "list"])
        assert result.exit_code == 0
        assert "pool1/v1" in result.output
        assert "pool1/v2" in result.output

    def test_list_filtered_by_pool(self, runner):
        volumes = [{"name": "v1", "pool_name": "pool1", "host_path": "/pools/pool1/v1"}]
        with patch("cep.cli.storage.volume.client") as mock_client:
            mock_client.get.return_value = _ok(volumes)
            result = runner.invoke(app, ["storage", "volume", "list", "--pool-name=pool1"])
        assert result.exit_code == 0
        mock_client.get.assert_called_once_with("", params={"pool_name": "pool1"})

    def test_list_empty(self, runner):
        with patch("cep.cli.storage.volume.client") as mock_client:
            mock_client.get.return_value = _ok([])
            result = runner.invoke(app, ["storage", "volume", "list"])
        assert result.exit_code == 0
        assert "No volumes" in result.output


class TestStorageVolumeShow:
    def test_show_prints_details(self, runner):
        info = {
            "name": "v1",
            "pool_name": "pool1",
            "host_path": "/pools/pool1/v1",
            "total_size_bytes": 2048,
            "created_at": "2025-01-01T00:00:00+00:00",
        }
        with patch("cep.cli.storage.volume.client") as mock_client:
            mock_client.get.return_value = _ok(info)
            result = runner.invoke(app, ["storage", "volume", "show", "pool1", "v1"])
        assert result.exit_code == 0
        assert "v1" in result.output
        assert "2048" in result.output

    def test_show_not_found(self, runner):
        with patch("cep.cli.storage.volume.client") as mock_client:
            mock_client.get.return_value = _err(404, "not found")
            result = runner.invoke(app, ["storage", "volume", "show", "pool1", "ghost"])
        assert result.exit_code == 0
        assert "not found" in result.output
