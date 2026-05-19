"""Tests for the /network server router via FastAPI TestClient."""
from __future__ import annotations

import ipaddress

import pytest

from cep.server.utils import load_db, save_db
from cep.datamodels import NetworkRecord, NetworkStore


@pytest.fixture()
def client(server_client):
    return server_client


class TestNetworkList:
    def test_empty(self, client):
        resp = client.get("/network/list")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_after_creating_network(self, client, populated_db):
        resp = client.get("/network/list")
        assert resp.status_code == 200
        assert "testnet" in resp.json()


class TestNetworkCreate:
    def test_create_returns_network_record(self, client):
        resp = client.get("/network/create", params={"name": "mynet", "dns": False})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "mynet"
        assert "subnet" in data
        # subnet must be a valid IPv6Network string
        ipaddress.IPv6Network(data["subnet"])

    def test_create_persists_to_db(self, client, server_dir):
        client.get("/network/create", params={"name": "mynet", "dns": False})
        store = load_db()
        assert "mynet" in store.networks

    def test_create_with_dns_false(self, client):
        resp = client.get("/network/create", params={"name": "dnsnet", "dns": False})
        assert resp.status_code == 200
        assert resp.json()["dns"] is False


class TestNetworkShow:
    def test_show_existing(self, client, populated_db):
        resp = client.get("/network/show", params={"name": "testnet"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "testnet"

    def test_show_nonexistent(self, client):
        resp = client.get("/network/show", params={"name": "ghost"})
        assert resp.status_code == 404


class TestNetworkDelete:
    def test_delete_existing(self, client, populated_db, server_dir):
        (server_dir / "testnet").mkdir(exist_ok=True)
        resp = client.delete("/network/delete", params={"name": "testnet"})
        assert resp.status_code == 200
        assert "testnet" not in load_db().networks

    def test_delete_nonexistent(self, client):
        resp = client.delete("/network/delete", params={"name": "ghost"})
        assert resp.status_code == 404


class TestNetworkLighthouses:
    def test_no_lighthouses(self, client, server_dir, mock_dns, mock_nebula_create_ca):
        client.get("/network/create", params={"name": "emptynet", "dns": False})
        resp = client.get("/network/lighthouses", params={"network_name": "emptynet"})
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_with_lighthouse(self, client, populated_db):
        resp = client.get("/network/lighthouses", params={"network_name": "testnet"})
        assert resp.status_code == 200
        data = resp.json()
        # One lighthouse exists; key is the nebula IP, value contains the port
        assert len(data) == 1
        value = list(data.values())[0]
        assert "4242" in value

    def test_nonexistent_network(self, client):
        resp = client.get("/network/lighthouses", params={"network_name": "ghost"})
        assert resp.status_code == 404
