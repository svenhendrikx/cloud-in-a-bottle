"""
Shared pytest fixtures for the CEP test suite.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from cep.datamodels import HostRecord, NetworkRecord, NetworkStore
from cep.cli.main import app as cli_app


# ---------------------------------------------------------------------------
# Server DB / filesystem isolation
# ---------------------------------------------------------------------------


@pytest.fixture()
def server_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Redirect all server-side DB and data paths to a fresh tmp directory.
    Patches both the utils module globals and every router that imported them
    by name.
    """
    sdir = tmp_path / "server"
    sdir.mkdir()
    db_path = sdir / "db.json"
    storage_db_path = sdir / "storage_db.json"

    monkeypatch.setattr("cep.server.utils.SERVER_DATA_DIR", sdir)
    monkeypatch.setattr("cep.server.utils.DB_PATH", db_path)
    monkeypatch.setattr("cep.server.utils.STORAGE_DB_PATH", storage_db_path)

    # Modules that imported SERVER_DATA_DIR by name
    monkeypatch.setattr("cep.server.network.SERVER_DATA_DIR", sdir)
    monkeypatch.setattr("cep.server.host.SERVER_DATA_DIR", sdir)

    return sdir


@pytest.fixture()
def mock_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suppress all outbound DNS-service HTTP calls made by server routers."""
    noop = lambda *args, **kwargs: MagicMock(status_code=200, content=b"ok")
    monkeypatch.setattr("cep.server.network.start_dns", lambda **kwargs: None)
    monkeypatch.setattr("cep.server.network.stop_dns", lambda: None)
    monkeypatch.setattr("cep.server.host.add_host_to_dns", noop)
    monkeypatch.setattr("cep.server.host.remove_host_from_dns", noop)


@pytest.fixture()
def mock_nebula_create_ca(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace network.create_ca so no real nebula-cert subprocess is needed."""
    def _fake_create_ca(name: str, ca_dir: Path) -> Path:
        (ca_dir / "ca.crt").write_text("fake-ca-cert")
        (ca_dir / "ca.key").write_text("fake-ca-key")
        return ca_dir

    monkeypatch.setattr("cep.server.network.create_ca", _fake_create_ca)


# ---------------------------------------------------------------------------
# Pre-populated NetworkStore helpers
# ---------------------------------------------------------------------------


def make_network_record(name: str = "testnet") -> NetworkRecord:
    import ipaddress
    return NetworkRecord(
        name=name,
        subnet=ipaddress.IPv6Network("fd12:3456:789a:1::/64"),
        hosts={},
        dns=False,
    )


def make_lighthouse_record(
    host_name: str = "lh1",
    network_name: str = "testnet",
) -> HostRecord:
    import ipaddress
    return HostRecord(
        name=host_name,
        ip=ipaddress.ip_address("fd12:3456:789a:1::1"),
        groups=[],
        is_lighthouse=True,
        public_ip=ipaddress.ip_address("1.2.3.4"),
    )


@pytest.fixture()
def populated_db(server_dir: Path) -> Path:
    """
    Write a db.json with one network ('testnet') containing one lighthouse,
    and also create the matching directory that network/list reads from.
    Returns the path to db.json.
    """
    from cep.server.utils import save_db

    store = NetworkStore(networks={})
    net = make_network_record()
    lh = make_lighthouse_record()
    net.hosts[lh.name] = lh
    store.networks[net.name] = net
    save_db(store)

    # network/list reads directories, not the DB
    (server_dir / "testnet").mkdir(exist_ok=True)

    return server_dir / "db.json"


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------


@pytest.fixture()
def server_client(server_dir, mock_dns, mock_nebula_create_ca, monkeypatch) -> TestClient:
    """
    TestClient for the main CEP server app with isolated DB and no auth.

    `instantiate_main_app()` reads CEP_SERVER_TOKEN at call-time, so we clear
    it here and build a fresh, token-free app for every test.
    """
    monkeypatch.delenv("CEP_SERVER_TOKEN", raising=False)
    from cep.server.main import instantiate_main_app
    fresh_app = instantiate_main_app()

    from cep.server import network, host, dns, storage
    from cep.server.apps import apps_router
    fresh_app.include_router(network.network_router)
    fresh_app.include_router(host.host_router)
    fresh_app.include_router(apps_router)
    fresh_app.include_router(dns.dns_router)
    fresh_app.include_router(storage.storage_router)

    return TestClient(fresh_app)


# ---------------------------------------------------------------------------
# Storage filesystem isolation
# ---------------------------------------------------------------------------


@pytest.fixture()
def storage_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Redirect cep.storage.docker storage paths to tmp_path.
    """
    storage_root = tmp_path / "storage"
    pools_dir = storage_root / "pools"
    pools_dir.mkdir(parents=True)

    monkeypatch.setattr("cep.storage.docker.STORAGE_ROOT", storage_root)
    monkeypatch.setattr("cep.storage.docker.POOLS_DIR", pools_dir)

    return storage_root


# ---------------------------------------------------------------------------
# Typer CLI runner
# ---------------------------------------------------------------------------


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# Dummy file helpers for CLI / bundle tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def dummy_nebula_files(tmp_path: Path):
    """Create minimal dummy nebula key/cert/ca files for bundle tests."""
    host_data = tmp_path / "host"
    host_data.mkdir()

    priv_key = host_data / "myhost.key"
    pub_key = host_data / "myhost.pub"
    crt = host_data / "myhost.crt"
    ca_crt = host_data / "ca.crt"
    config = host_data / "config.yml"

    for f in [priv_key, pub_key, crt, ca_crt, config]:
        f.write_text(f"dummy-content-{f.name}")

    return {
        "host_data": host_data,
        "priv_key_path": priv_key,
        "pub_key_path": pub_key,
        "crt_path": crt,
        "ca_crt_path": ca_crt,
        "config_out_path": config,
    }
