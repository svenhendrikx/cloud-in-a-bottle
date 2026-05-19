"""Tests for cep.server.utils – DB load/save roundtrips."""
from __future__ import annotations

import ipaddress

import pytest

from cep.datamodels import HostRecord, NetworkRecord, NetworkStore, StorageStore
from cep.server.utils import load_db, load_storage_db, save_db, save_storage_db


class TestNetworkDB:
    def test_empty_db_when_no_file(self, server_dir):
        store = load_db()
        assert store.networks == {}

    def test_save_and_load_roundtrip(self, server_dir):
        store = NetworkStore(networks={})
        net = NetworkRecord(
            name="testnet",
            subnet=ipaddress.IPv6Network("fd12:3456:789a:1::/64"),
            hosts={},
            dns=False,
        )
        store.networks["testnet"] = net
        save_db(store)

        loaded = load_db()
        assert "testnet" in loaded.networks
        assert loaded.networks["testnet"].name == "testnet"
        assert loaded.networks["testnet"].subnet == net.subnet

    def test_save_with_hosts(self, server_dir):
        store = NetworkStore(networks={})
        net = NetworkRecord(
            name="testnet",
            subnet=ipaddress.IPv6Network("fd12:3456:789a:1::/64"),
            hosts={},
            dns=False,
        )
        host = HostRecord(
            name="lh1",
            ip=ipaddress.ip_address("fd12:3456:789a:1::1"),
            groups=[],
            is_lighthouse=True,
            public_ip=ipaddress.ip_address("1.2.3.4"),
        )
        net.hosts["lh1"] = host
        store.networks["testnet"] = net
        save_db(store)

        loaded = load_db()
        assert "lh1" in loaded.networks["testnet"].hosts
        assert str(loaded.networks["testnet"].hosts["lh1"].public_ip) == "1.2.3.4"

    def test_overwrite_saves_latest(self, server_dir):
        store = NetworkStore(networks={})
        net = NetworkRecord(name="net1", subnet="fd12::/64", hosts={}, dns=False)
        store.networks["net1"] = net
        save_db(store)

        store2 = load_db()
        net2 = NetworkRecord(name="net2", subnet="fd13::/64", hosts={}, dns=True)
        store2.networks["net2"] = net2
        save_db(store2)

        final = load_db()
        assert "net1" in final.networks
        assert "net2" in final.networks


class TestStorageDB:
    def test_empty_when_no_file(self, server_dir):
        store = load_storage_db()
        assert store.pools == {}
        assert store.volumes == {}

    def test_save_and_load_roundtrip(self, server_dir):
        from cep.datamodels import PoolRecord, VolumeRecord
        store = StorageStore()
        store.pools["p1"] = PoolRecord(name="p1", path="/pools/p1", created_at="2025-01-01T00:00:00+00:00")
        store.volumes["p1/v1"] = VolumeRecord(
            name="v1", pool_name="p1", host_path="/pools/p1/v1", created_at="2025-01-01T00:00:00+00:00"
        )
        save_storage_db(store)

        loaded = load_storage_db()
        assert "p1" in loaded.pools
        assert "p1/v1" in loaded.volumes
