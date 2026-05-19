"""
Tests for generate_ula_prefix and create_ca.

TODO references:
  server/network.py:25 – "last 64 bits needs to be zero valued, needs to return valid IPv6"
  server/network.py:32 – create_ca

generate_ula_prefix:
- Returns an IPv6Network with prefix length /64
- First byte is 0xfd (Unique Local Address)
- Network address has the last 64 bits zeroed (host part is zero)
- Is globally unique – two consecutive calls produce different prefixes

create_ca:
- Invokes nebula-cert with the correct arguments
- Moves the generated ca.* files from cwd into ca_dir
- Returns ca_dir
"""
from __future__ import annotations

import ipaddress
from pathlib import Path
from unittest.mock import call, patch, MagicMock

import pytest

from cep.server.network import generate_ula_prefix, create_ca


class TestGenerateUlaPrefix:
    def test_returns_ipv6_network(self):
        result = generate_ula_prefix()
        assert isinstance(result, ipaddress.IPv6Network)

    def test_prefix_length_is_64(self):
        result = generate_ula_prefix()
        assert result.prefixlen == 64, f"Expected /64 but got /{result.prefixlen}"

    def test_first_byte_is_fd(self):
        """ULA addresses must start with 0xfd (fc00::/7 with L-bit set)."""
        result = generate_ula_prefix()
        first_byte = int(result.network_address) >> 120
        assert first_byte == 0xfd, f"Expected first byte 0xfd, got 0x{first_byte:02x}"

    def test_last_64_bits_of_network_address_are_zero(self):
        """
        The host part of the network address must be all zeros –
        only the upper 64 bits (the prefix) should be non-zero.
        """
        result = generate_ula_prefix()
        network_int = int(result.network_address)
        last_64 = network_int & ((1 << 64) - 1)
        assert last_64 == 0, (
            f"Expected lower 64 bits to be 0, got {last_64:#x}"
        )

    def test_uniqueness_across_calls(self):
        """Two independent calls should (with overwhelming probability) differ."""
        results = {generate_ula_prefix() for _ in range(10)}
        assert len(results) > 1, "generate_ula_prefix returned identical values – RNG may be broken"


class TestCreateCa:
    def test_calls_nebula_cert_with_correct_args(self, tmp_path, monkeypatch):
        ca_dir = tmp_path / "ca"
        ca_dir.mkdir()
        fake_bin = "/fake/nebula-cert"

        monkeypatch.setattr("cep.server.network.get_executable_path", lambda _: fake_bin)
        monkeypatch.chdir(tmp_path)

        # nebula-cert would normally create ca.crt and ca.key in cwd
        (tmp_path / "ca.crt").write_text("cert")
        (tmp_path / "ca.key").write_text("key")

        with patch("cep.server.network.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            create_ca("mynet", ca_dir)

        mock_run.assert_called_once_with(
            [fake_bin, "ca", "-name", "mynet"],
            capture_output=True,
            text=True,
        )

    def test_moves_ca_files_into_ca_dir(self, tmp_path, monkeypatch):
        ca_dir = tmp_path / "ca"
        ca_dir.mkdir()

        monkeypatch.setattr("cep.server.network.get_executable_path", lambda _: "/fake/nebula-cert")
        monkeypatch.chdir(tmp_path)

        (tmp_path / "ca.crt").write_text("fake-cert")
        (tmp_path / "ca.key").write_text("fake-key")

        with patch("cep.server.network.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            create_ca("mynet", ca_dir)

        assert (ca_dir / "ca.crt").exists(), "ca.crt should have been moved into ca_dir"
        assert (ca_dir / "ca.key").exists(), "ca.key should have been moved into ca_dir"
        assert not (tmp_path / "ca.crt").exists(), "ca.crt should no longer be in cwd"
        assert not (tmp_path / "ca.key").exists(), "ca.key should no longer be in cwd"

    def test_returns_ca_dir(self, tmp_path, monkeypatch):
        ca_dir = tmp_path / "ca"
        ca_dir.mkdir()

        monkeypatch.setattr("cep.server.network.get_executable_path", lambda _: "/fake/nebula-cert")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "ca.crt").write_text("cert")
        (tmp_path / "ca.key").write_text("key")

        with patch("cep.server.network.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = create_ca("mynet", ca_dir)

        assert result == ca_dir
