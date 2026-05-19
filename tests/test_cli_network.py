"""
Tests for the network CLI sub-commands.

All HTTP calls are intercepted with unittest.mock so no real server is needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cep.cli.main import app


@pytest.fixture()
def runner():
    return CliRunner()


def _ok(json_data):
    """Return a mock httpx Response with a given JSON payload."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


def _err(status_code: int = 404):
    import httpx
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )
    return mock


class TestNetworkList:
    def test_list_outputs_names(self, runner):
        with patch("cep.cli.network.client") as mock_client:
            mock_client.get.return_value = _ok(["net1", "net2"])
            result = runner.invoke(app, ["network", "list"])
        assert result.exit_code == 0
        assert "net1" in result.output
        assert "net2" in result.output

    def test_list_empty(self, runner):
        with patch("cep.cli.network.client") as mock_client:
            mock_client.get.return_value = _ok([])
            result = runner.invoke(app, ["network", "list"])
        assert result.exit_code == 0

    def test_list_server_error_exits_nonzero(self, runner):
        with patch("cep.cli.network.client") as mock_client:
            mock_client.get.return_value = _err(500)
            result = runner.invoke(app, ["network", "list"])
        assert result.exit_code != 0


class TestNetworkCreate:
    def test_create_calls_server(self, runner):
        with patch("cep.cli.network.client") as mock_client:
            mock_client.get.return_value = _ok({})
            result = runner.invoke(app, ["network", "create", "mynet"])
        assert result.exit_code == 0
        mock_client.get.assert_called_once()
        call_kwargs = mock_client.get.call_args
        assert "mynet" in str(call_kwargs)

    def test_create_with_dns_flag(self, runner):
        with patch("cep.cli.network.client") as mock_client:
            mock_client.get.return_value = _ok({})
            result = runner.invoke(app, ["network", "create", "mynet", "--dns"])
        assert result.exit_code == 0


class TestNetworkShow:
    def test_show_prints_data(self, runner):
        payload = {"name": "mynet", "subnet": "fd12::/64", "hosts": {}, "dns": False}
        with patch("cep.cli.network.client") as mock_client:
            mock_client.get.return_value = _ok(payload)
            result = runner.invoke(app, ["network", "show", "mynet"])
        assert result.exit_code == 0
        assert "mynet" in result.output


class TestNetworkDelete:
    def test_delete_calls_server_and_removes_dir(self, runner, tmp_path):
        net_dir = tmp_path / "mynet"
        net_dir.mkdir()
        with patch("cep.cli.network.client") as mock_client, \
             patch("cep.cli.network.CLI_DATA_DIR", tmp_path):
            mock_client.delete.return_value = _ok({})
            result = runner.invoke(app, ["network", "delete", "mynet"])
        assert result.exit_code == 0
        # shutil.rmtree should have removed the directory
        assert not net_dir.exists()


class TestNetworkLighthouses:
    def test_lighthouses_prints_mapping(self, runner):
        payload = {"fd12::1": "1.2.3.4:4242"}
        with patch("cep.cli.network.client") as mock_client:
            mock_client.get.return_value = _ok(payload)
            result = runner.invoke(app, ["network", "lighthouses", "mynet"])
        assert result.exit_code == 0
        assert "fd12" in result.output
