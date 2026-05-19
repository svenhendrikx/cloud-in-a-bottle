"""
Tests for the host CLI sub-commands.

HTTP clients, subprocess calls (nebula-cert), and filesystem paths are all
mocked so the tests run without any real infrastructure.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

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
    if json_data is not None:
        mock.json.return_value = json_data
    if content is not None:
        mock.content = content
    return mock


def _make_zip_bytes(filename: str = "ca.crt", text: str = "fake-cert") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, text)
        zf.writestr("myhost.crt", "fake-crt")
    return buf.getvalue()


class TestHostList:
    def test_list_returns_host_names(self, runner, tmp_path):
        net_dir = tmp_path / "mynet"
        (net_dir / "host1").mkdir(parents=True)
        (net_dir / "host2").mkdir(parents=True)

        result = runner.invoke(app, ["host", "list", "mynet", f"--data-dir={tmp_path}"])

        assert result.exit_code == 0
        assert "host1" in result.output
        assert "host2" in result.output


class TestHostCreate:
    def _run_create(self, runner, tmp_path, *, lighthouse=False, public_ip="1.2.3.4"):
        """Helper – patches everything needed for host create."""
        network_client = MagicMock()
        network_client.get.return_value = _ok(
            {"fd12::1": "1.2.3.4:4242"} if not lighthouse else {}
        )

        host_client = MagicMock()
        host_client.post.side_effect = [
            _ok({"ip": "fd12::2", "name": "myhost", "is_lighthouse": lighthouse}),  # /create
            _ok(content=_make_zip_bytes()),                                          # /sign
        ]

        fake_subprocess = MagicMock()
        fake_subprocess.run.return_value = MagicMock(returncode=0)

        pub_key_file = tmp_path / "myhost.pub"
        pub_key_file.write_text("fake-pub-key")

        config_template = {
            "pki": {},
            "lighthouse": {},
            "firewall": {"inbound": [], "outbound": []},
            "static_host_map": {},
        }

        args = ["host", "create", "mynet", "myhost", f"--output-dir={tmp_path}"]
        if lighthouse:
            args += ["--am-lighthouse", f"--public-ip={public_ip}"]

        with patch("cep.cli.host.CLI_DATA_DIR", tmp_path), \
             patch("cep.cli.host.client", host_client), \
             patch("cep.cli.host.get_client", return_value=network_client), \
             patch("cep.cli.host.subprocess", fake_subprocess), \
             patch("cep.cli.host.get_executable_path", return_value="/fake/nebula-cert"), \
             patch("builtins.open", mock_open(read_data="fake-pub-key")), \
             patch("cep.cli.host.yaml.safe_load", return_value=config_template), \
             patch("cep.cli.host.yaml.safe_dump"), \
             patch("cep.cli.host.zipfile.ZipFile") as mock_zf:
            mock_zf.return_value.__enter__.return_value.extractall = MagicMock()
            result = runner.invoke(app, args)

        return result

    def test_create_non_lighthouse(self, runner, tmp_path):
        result = self._run_create(runner, tmp_path, lighthouse=False)
        assert result.exit_code == 0

    def test_create_lighthouse(self, runner, tmp_path):
        result = self._run_create(runner, tmp_path, lighthouse=True)
        assert result.exit_code == 0

    def test_create_lighthouse_without_public_ip_exits(self, runner, tmp_path):
        with patch("cep.cli.host.CLI_DATA_DIR", tmp_path):
            result = runner.invoke(app, ["host", "create", "mynet", "myhost", "--am-lighthouse"])
        assert result.exit_code != 0


class TestHostDelete:
    def test_delete_calls_server_and_removes_dir(self, runner, tmp_path):
        host_dir = tmp_path / "mynet" / "myhost"
        host_dir.mkdir(parents=True)

        host_client = MagicMock()
        host_client.delete.return_value = _ok({"status": "deleted"})

        with patch("cep.cli.host.CLI_DATA_DIR", tmp_path), \
             patch("cep.cli.host.client", host_client):
            result = runner.invoke(app, ["host", "delete", "mynet", "myhost"])

        assert result.exit_code == 0
        assert not host_dir.exists()


class TestHostShow:
    def test_show_prints_combined_data(self, runner, tmp_path):
        host_dir = tmp_path / "mynet" / "myhost"
        host_dir.mkdir(parents=True)
        config_file = host_dir / "config.yml"
        config_file.write_text("pki: {}")

        host_client = MagicMock()
        host_client.get.return_value = _ok({"name": "myhost", "ip": "fd12::2"})

        with patch("cep.cli.host.CLI_DATA_DIR", tmp_path), \
             patch("cep.cli.host.client", host_client), \
             patch("cep.cli.host.yaml.safe_load", return_value={"pki": {}}):
            result = runner.invoke(app, ["host", "show", "mynet", "myhost"])

        assert result.exit_code == 0
        assert "myhost" in result.output
