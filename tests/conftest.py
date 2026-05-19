"""Shared fixtures for the CEP unit test suite."""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cep.datamodels import HostRecord, NetworkRecord, NetworkStore


# ---------------------------------------------------------------------------
# Isolated server DB (patches module-level globals in-place)
# ---------------------------------------------------------------------------

@pytest.fixture()
def server_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Redirect every server-side path reference to a fresh tmp directory so
    tests never touch real user data.
    """
    sdir = tmp_path / "server"
    sdir.mkdir()
    db_path = sdir / "db.json"

    monkeypatch.setattr("cep.server.utils.SERVER_DATA_DIR", sdir)
    monkeypatch.setattr("cep.server.utils.DB_PATH", db_path)
    monkeypatch.setattr("cep.server.network.SERVER_DATA_DIR", sdir)
    monkeypatch.setattr("cep.server.host.SERVER_DATA_DIR", sdir)

    return sdir


@pytest.fixture()
def mock_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suppress all outbound DNS-service HTTP calls."""
    monkeypatch.setattr("cep.server.network.start_dns", lambda **kwargs: None)
    monkeypatch.setattr("cep.server.network.stop_dns", lambda: None)
    monkeypatch.setattr("cep.server.host.add_host_to_dns", lambda *a, **kw: None)
    monkeypatch.setattr("cep.server.host.remove_host_from_dns", lambda *a, **kw: None)


@pytest.fixture()
def mock_create_ca(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace create_ca so no real nebula-cert subprocess is needed."""
    def _fake(name: str, ca_dir: Path) -> Path:
        (ca_dir / "ca.crt").write_text("fake-ca-cert")
        (ca_dir / "ca.key").write_text("fake-ca-key")
        return ca_dir

    monkeypatch.setattr("cep.server.network.create_ca", _fake)


# ---------------------------------------------------------------------------
# FastAPI TestClient (token-free, isolated DB)
# ---------------------------------------------------------------------------

@pytest.fixture()
def api(server_dir, mock_dns, mock_create_ca, monkeypatch) -> TestClient:
    """
    TestClient for the CEP main server with isolated DB and no auth.
    A fresh app instance is built so CEP_SERVER_TOKEN has no effect.
    """
    monkeypatch.delenv("CEP_SERVER_TOKEN", raising=False)

    from cep.server.main import instantiate_main_app
    from cep.server import network, host, dns, storage
    from cep.server.apps import apps_router

    app = instantiate_main_app()
    app.include_router(network.network_router)
    app.include_router(host.host_router)
    app.include_router(apps_router)
    app.include_router(dns.dns_router)
    app.include_router(storage.storage_router)

    return TestClient(app)


# ---------------------------------------------------------------------------
# Pre-seeded DB helper
# ---------------------------------------------------------------------------

def seed_network(server_dir: Path, *, name: str = "testnet", dns: bool = False) -> NetworkRecord:
    """Write a network (no hosts) directly into the DB and create its dir."""
    from cep.server.utils import load_db, save_db

    net = NetworkRecord(
        name=name,
        subnet=ipaddress.IPv6Network("fd12:3456:789a:1::/64"),
        hosts={},
        dns=dns,
    )
    store = load_db()
    store.networks[name] = net
    save_db(store)
    (server_dir / name).mkdir(exist_ok=True)
    return net
