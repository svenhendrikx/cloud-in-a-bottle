"""
Tests for the /network/delete and /network/show router endpoints.

TODO references:
  server/network.py:73 – "make sure network_record deletion is tested"
  server/network.py:100 – "create dummy database and check if the contents match the spec"

delete:
- Removes the network directory from SERVER_DATA_DIR
- Removes the network record from the DB
- Returns 404 when the directory does not exist
- Returns 404 when the record is not in the DB (but directory exists)
- Calls stop_dns only when the network had DNS enabled

show:
- Returns the full NetworkRecord (name, subnet, dns flag, hosts)
- Returned subnet matches exactly what was stored
- Returned dns flag matches exactly what was stored
- Returns 404 for an unknown network name
"""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path

import pytest

from cep.datamodels import NetworkRecord, NetworkStore
from cep.server.utils import load_db, save_db
from tests.conftest import seed_network


class TestNetworkDelete:
    def test_directory_is_removed_after_delete(self, api, server_dir):
        seed_network(server_dir, name="mynet")
        net_dir = server_dir / "mynet"
        assert net_dir.exists()

        api.delete("/network/delete", params={"name": "mynet"})

        assert not net_dir.exists(), "Network directory must be deleted"

    def test_db_record_is_removed_after_delete(self, api, server_dir):
        seed_network(server_dir, name="mynet")

        api.delete("/network/delete", params={"name": "mynet"})

        store = load_db()
        assert "mynet" not in store.networks, "Network record must be removed from DB"

    def test_returns_404_when_directory_missing(self, api, server_dir):
        # Insert DB record but intentionally omit the directory
        net = NetworkRecord(name="ghost", subnet="fd00::/64", hosts={}, dns=False)
        store = NetworkStore(networks={"ghost": net})
        save_db(store)
        # directory NOT created

        resp = api.delete("/network/delete", params={"name": "ghost"})
        assert resp.status_code == 404

    def test_returns_404_when_record_not_in_db(self, api, server_dir):
        # Create directory but no DB record
        (server_dir / "orphan").mkdir()

        resp = api.delete("/network/delete", params={"name": "orphan"})
        assert resp.status_code == 404

    def test_stop_dns_called_when_dns_enabled(self, api, server_dir, monkeypatch):
        seed_network(server_dir, name="dnsnet", dns=True)
        stop_calls = []
        monkeypatch.setattr("cep.server.network.stop_dns", lambda: stop_calls.append(True))

        api.delete("/network/delete", params={"name": "dnsnet"})

        assert len(stop_calls) == 1, "stop_dns must be called when network had DNS enabled"

    def test_stop_dns_not_called_when_dns_disabled(self, api, server_dir, monkeypatch):
        seed_network(server_dir, name="nodnsnet", dns=False)
        stop_calls = []
        monkeypatch.setattr("cep.server.network.stop_dns", lambda: stop_calls.append(True))

        api.delete("/network/delete", params={"name": "nodnsnet"})

        assert len(stop_calls) == 0, "stop_dns must NOT be called when DNS was disabled"


class TestNetworkShow:
    def test_returns_correct_name(self, api, server_dir):
        seed_network(server_dir, name="mynet")
        resp = api.get("/network/show", params={"name": "mynet"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "mynet"

    def test_returned_subnet_matches_stored_value(self, api, server_dir):
        seed_network(server_dir, name="mynet")
        resp = api.get("/network/show", params={"name": "mynet"})
        assert resp.status_code == 200
        # seed_network always uses fd12:3456:789a:1::/64
        assert resp.json()["subnet"] == "fd12:3456:789a:1::/64"

    def test_returned_dns_flag_matches_stored_true(self, api, server_dir):
        seed_network(server_dir, name="dnsnet", dns=True)
        resp = api.get("/network/show", params={"name": "dnsnet"})
        assert resp.status_code == 200
        assert resp.json()["dns"] is True

    def test_returned_dns_flag_matches_stored_false(self, api, server_dir):
        seed_network(server_dir, name="nodnsnet", dns=False)
        resp = api.get("/network/show", params={"name": "nodnsnet"})
        assert resp.status_code == 200
        assert resp.json()["dns"] is False

    def test_returned_hosts_dict_matches_stored(self, api, server_dir):
        """A network with no hosts must return an empty hosts dict."""
        seed_network(server_dir, name="emptynet")
        resp = api.get("/network/show", params={"name": "emptynet"})
        assert resp.status_code == 200
        assert resp.json()["hosts"] == {}

    def test_returns_404_for_unknown_network(self, api, server_dir):
        resp = api.get("/network/show", params={"name": "doesnotexist"})
        assert resp.status_code == 404
