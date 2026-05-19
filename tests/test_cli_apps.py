"""
Tests for the apps CLI sub-commands.

All HTTP calls are intercepted so no real server is needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cep.cli.main import app


@pytest.fixture()
def runner():
    return CliRunner()


def _ok(json_data=None, *, content: bytes = None):
    mock = MagicMock()
    mock.status_code = 200
    mock.raise_for_status.return_value = None
    mock.json.return_value = json_data if json_data is not None else {}
    if content is not None:
        mock.content = content
    else:
        import json as _json
        mock.content = _json.dumps(json_data).encode() if json_data is not None else b"{}"
    return mock


def _err(status_code: int = 500, detail: str = "server error"):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {"detail": detail}
    import httpx
    mock.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )
    return mock


# ---------------------------------------------------------------------------
# apps deploy
# ---------------------------------------------------------------------------

class TestAppsDeploy:
    def test_deploy_single_app(self, runner):
        with patch("cep.cli.apps.client_proxy") as mock_client:
            mock_client.post.return_value = _ok()
            result = runner.invoke(app, ["apps", "deploy", "nginx"])
        assert result.exit_code == 0
        mock_client.post.assert_called_once()

    def test_deploy_multiple_apps(self, runner):
        with patch("cep.cli.apps.client_proxy") as mock_client:
            mock_client.post.return_value = _ok()
            result = runner.invoke(app, ["apps", "deploy", "nginx", "redis"])
        assert result.exit_code == 0
        assert mock_client.post.call_count == 2


# ---------------------------------------------------------------------------
# apps list
# ---------------------------------------------------------------------------

class TestAppsList:
    def test_list_prints_content(self, runner):
        with patch("cep.cli.apps.client_proxy") as mock_client:
            mock_client.get.return_value = _ok(content=b'["nginx","redis"]')
            result = runner.invoke(app, ["apps", "list"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# apps store list
# ---------------------------------------------------------------------------

class TestAppsStoreList:
    def test_store_list_prints_app_names(self, runner):
        with patch("cep.cli.apps.store.client_proxy") as mock_client:
            mock_client.get.return_value = _ok(["nginx", "redis"])
            result = runner.invoke(app, ["apps", "store", "list"])
        assert result.exit_code == 0
        assert "nginx" in result.output
        assert "redis" in result.output

    def test_store_list_empty(self, runner):
        with patch("cep.cli.apps.store.client_proxy") as mock_client:
            mock_client.get.return_value = _ok([])
            result = runner.invoke(app, ["apps", "store", "list"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# apps targeted-destroy
# ---------------------------------------------------------------------------

class TestAppsTargetedDestroy:
    def test_destroy_single(self, runner):
        with patch("cep.cli.apps.client_proxy") as mock_client:
            mock_client.delete.return_value = _ok()
            result = runner.invoke(app, ["apps", "targeted-destroy", "nginx"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()

    def test_destroy_multiple(self, runner):
        with patch("cep.cli.apps.client_proxy") as mock_client:
            mock_client.delete.return_value = _ok()
            result = runner.invoke(app, ["apps", "targeted-destroy", "nginx", "redis"])
        assert result.exit_code == 0
        assert mock_client.delete.call_count == 2


# ---------------------------------------------------------------------------
# apps clear
# ---------------------------------------------------------------------------

class TestAppsClear:
    def test_clear(self, runner):
        with patch("cep.cli.apps.client_proxy") as mock_client:
            mock_client.delete.return_value = _ok()
            result = runner.invoke(app, ["apps", "clear"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once()
