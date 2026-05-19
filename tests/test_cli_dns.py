"""
Tests for NebulaDNS helpers and the dns CLI commands.

Subprocess / scutil calls are mocked so no OS-level DNS changes are made.
"""
from __future__ import annotations

import platform
from unittest.mock import MagicMock, patch, call

import pytest
from typer.testing import CliRunner

from cep.cli.dns import NebulaDNS
from cep.cli.main import app


# ---------------------------------------------------------------------------
# NebulaDNS unit tests
# ---------------------------------------------------------------------------


class TestNebulaDNSInit:
    def test_empty_dns_ips_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            NebulaDNS(nebula_dns_ips=[], domain="mynet")

    def test_valid_init(self):
        dns = NebulaDNS(nebula_dns_ips=["10.0.0.1"], domain="mynet")
        assert dns.domain == "mynet"
        assert dns.nebula_dns_servers == ["10.0.0.1"]


class TestNebulaDNSExtractDnsServers:
    def test_extracts_ipv4(self):
        dns = NebulaDNS.__new__(NebulaDNS)
        dns.nebula_dns_servers = []
        dns.iface = "nebula1"
        dns.domain = "net"
        dns.os = "linux"
        dns._stop_event = MagicMock()
        dns.dns_thread = None

        output = "  <dictionary> {\n    0 : 8.8.8.8\n    1 : 1.1.1.1\n  }"
        servers = dns._extract_dns_servers(output)
        assert "8.8.8.8" in servers
        assert "1.1.1.1" in servers

    def test_extracts_ipv6(self):
        dns = NebulaDNS.__new__(NebulaDNS)
        output = "  0 : fd12::1"
        servers = dns._extract_dns_servers(output)
        assert "fd12::1" in servers


class TestNebulaDNSLinux:
    def test_enable_linux_calls_resolvectl(self):
        with patch("cep.cli.dns.platform.system", return_value="Linux"), \
             patch("cep.cli.dns.run") as mock_run:
            dns = NebulaDNS.__new__(NebulaDNS)
            dns.nebula_dns_servers = ["fd12::1"]
            dns.iface = "nebula1"
            dns.domain = "mynet"
            dns.os = "linux"
            dns._stop_event = MagicMock()
            dns.dns_thread = None

            dns._enable_linux()

        assert mock_run.call_count == 2
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "resolvectl" in first_call_args
        assert "dns" in first_call_args

    def test_disable_linux_is_noop(self):
        dns = NebulaDNS.__new__(NebulaDNS)
        dns.nebula_dns_servers = ["fd12::1"]
        dns.iface = "nebula1"
        dns.domain = "mynet"
        dns.os = "linux"
        # disable is a no-op currently – should not raise
        dns._disable_linux()


class TestNebulaDNSUnsupportedOS:
    def test_enable_unsupported_raises(self):
        with patch("cep.cli.dns.platform.system", return_value="Windows"):
            dns = NebulaDNS.__new__(NebulaDNS)
            dns.nebula_dns_servers = ["1.1.1.1"]
            dns.iface = "nebula1"
            dns.domain = "net"
            dns.os = "windows"
            dns._stop_event = MagicMock()
            dns.dns_thread = None

        with pytest.raises(NotImplementedError):
            dns.enable()

    def test_disable_unsupported_raises(self):
        dns = NebulaDNS.__new__(NebulaDNS)
        dns.os = "windows"
        dns._stop_event = MagicMock()
        dns.dns_thread = None
        with pytest.raises(NotImplementedError):
            dns.disable()


# ---------------------------------------------------------------------------
# DNS CLI command tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner():
    return CliRunner()


def _ok():
    m = MagicMock()
    m.raise_for_status.return_value = None
    return m


class TestDnsCLI:
    def test_dns_start(self, runner):
        with patch("cep.cli.dns.client") as mock_client:
            mock_client.post.return_value = _ok()
            result = runner.invoke(app, ["dns", "start", "mynet"])
        assert result.exit_code == 0
        mock_client.post.assert_called_once_with("/start", json={"network_name": "mynet"})

    def test_dns_stop(self, runner):
        with patch("cep.cli.dns.client") as mock_client:
            mock_client.post.return_value = _ok()
            result = runner.invoke(app, ["dns", "stop"])
        assert result.exit_code == 0

    def test_dns_add(self, runner):
        with patch("cep.cli.dns.client") as mock_client:
            mock_client.post.return_value = _ok()
            result = runner.invoke(app, ["dns", "add", "host.mynet", "fd12::2"])
        assert result.exit_code == 0
        call_json = mock_client.post.call_args[1]["json"]
        assert call_json["name"] == "host.mynet"
        assert call_json["ip"] == "fd12::2"

    def test_dns_remove(self, runner):
        with patch("cep.cli.dns.client") as mock_client:
            mock_client.delete.return_value = _ok()
            result = runner.invoke(app, ["dns", "remove", "host.mynet"])
        assert result.exit_code == 0
        mock_client.delete.assert_called_once_with("/records/host.mynet")
