"""Tests for the /host server router via FastAPI TestClient."""
from __future__ import annotations

import ipaddress

import pytest

from cep.server.utils import load_db


@pytest.fixture()
def client(server_client):
    return server_client


class TestHostCreate:
    def test_create_first_host_as_lighthouse(self, client, populated_db):
        # 'testnet' already has a lighthouse – add a regular node
        resp = client.post("/host/create", json={
            "name": "node1",
            "network_name": "testnet",
            "is_lighthouse": False,
            "public_ip": None,
            "add_dns_record": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "node1"
        assert data["is_lighthouse"] is False
        assert "ip" in data

    def test_create_lighthouse_in_new_network(self, client, server_dir, mock_dns, mock_nebula_create_ca):
        client.get("/network/create", params={"name": "freshnet", "dns": False})
        resp = client.post("/host/create", json={
            "name": "lh1",
            "network_name": "freshnet",
            "is_lighthouse": True,
            "public_ip": "203.0.113.1",
            "add_dns_record": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_lighthouse"] is True
        assert data["public_ip"] == "203.0.113.1"

    def test_create_host_in_unknown_network(self, client):
        resp = client.post("/host/create", json={
            "name": "node1",
            "network_name": "ghost",
            "is_lighthouse": False,
            "add_dns_record": False,
        })
        assert resp.status_code == 404

    def test_create_duplicate_host_returns_409(self, client, populated_db):
        # 'lh1' already exists in testnet
        resp = client.post("/host/create", json={
            "name": "lh1",
            "network_name": "testnet",
            "is_lighthouse": False,
            "add_dns_record": False,
        })
        assert resp.status_code == 409

    def test_first_host_gets_first_ip(self, client, server_dir, mock_dns, mock_nebula_create_ca):
        client.get("/network/create", params={"name": "firstnet", "dns": False})
        store = load_db()
        subnet = store.networks["firstnet"].subnet
        expected_first_ip = str(next(subnet.hosts()))

        resp = client.post("/host/create", json={
            "name": "lh1",
            "network_name": "firstnet",
            "is_lighthouse": True,
            "public_ip": "1.2.3.4",
            "add_dns_record": False,
        })
        assert resp.status_code == 200
        assert resp.json()["ip"] == expected_first_ip


class TestHostShow:
    def test_show_existing(self, client, populated_db):
        resp = client.get("/host/show", params={"network_name": "testnet", "host_name": "lh1"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "lh1"

    def test_show_unknown_network(self, client):
        resp = client.get("/host/show", params={"network_name": "ghost", "host_name": "lh1"})
        assert resp.status_code == 404

    def test_show_unknown_host(self, client, populated_db):
        resp = client.get("/host/show", params={"network_name": "testnet", "host_name": "ghost"})
        assert resp.status_code == 404


class TestHostDelete:
    def test_delete_existing(self, client, populated_db):
        resp = client.delete("/host/delete", params={"network_name": "testnet", "host_name": "lh1"})
        assert resp.status_code == 200
        store = load_db()
        assert "lh1" not in store.networks["testnet"].hosts

    def test_delete_nonexistent(self, client, populated_db):
        resp = client.delete("/host/delete", params={"network_name": "testnet", "host_name": "ghost"})
        assert resp.status_code == 404
