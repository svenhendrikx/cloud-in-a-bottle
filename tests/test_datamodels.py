"""Tests for cep.datamodels – Pydantic model validation and serialization."""
from __future__ import annotations

import ipaddress

import pytest
from pydantic import ValidationError

from cep.datamodels import (
    AddAAAARequest,
    CertificateRequest,
    HostRecord,
    HostRequest,
    NetworkRecord,
    NetworkStore,
    PoolRecord,
    StorageStore,
    VolumeRecord,
)


class TestNetworkRecord:
    def test_create_valid(self):
        net = NetworkRecord(
            name="mynet",
            subnet="fd12:3456:789a:1::/64",
            hosts={},
            dns=True,
        )
        assert net.name == "mynet"
        assert isinstance(net.subnet, ipaddress.IPv6Network)

    def test_subnet_roundtrip(self):
        net = NetworkRecord(name="mynet", subnet="fd12:3456:789a:1::/64", hosts={}, dns=False)
        data = net.model_dump()
        assert isinstance(data["subnet"], str)
        restored = NetworkRecord.model_validate(data)
        assert restored.subnet == net.subnet

    def test_invalid_subnet_raises(self):
        with pytest.raises(ValidationError):
            NetworkRecord(name="bad", subnet="not-a-subnet", hosts={}, dns=False)


class TestHostRecord:
    def test_lighthouse_requires_public_ip(self):
        with pytest.raises(ValidationError, match="Lighthouses must have a public_ip"):
            HostRecord(name="lh", ip="fd12::1", groups=[], is_lighthouse=True)

    def test_non_lighthouse_forbids_public_ip(self):
        with pytest.raises(ValidationError, match="Non-lighthouses must not have a public_ip"):
            HostRecord(name="node", ip="fd12::2", groups=[], is_lighthouse=False, public_ip="1.2.3.4")

    def test_valid_lighthouse(self):
        h = HostRecord(name="lh", ip="fd12::1", groups=[], is_lighthouse=True, public_ip="1.2.3.4")
        assert h.is_lighthouse is True
        assert str(h.public_ip) == "1.2.3.4"

    def test_valid_node(self):
        h = HostRecord(name="node", ip="fd12::2", groups=["workers"], is_lighthouse=False)
        assert h.public_ip is None

    def test_ip_serialized_as_string(self):
        h = HostRecord(name="node", ip="fd12::2", groups=[], is_lighthouse=False)
        assert isinstance(h.model_dump()["ip"], str)

    def test_ip_roundtrip(self):
        h = HostRecord(name="lh", ip="fd12::1", groups=[], is_lighthouse=True, public_ip="203.0.113.10")
        restored = HostRecord.model_validate(h.model_dump())
        assert restored.ip == h.ip
        assert restored.public_ip == h.public_ip


class TestHostRequest:
    def test_lighthouse_without_public_ip_raises(self):
        with pytest.raises(ValidationError):
            HostRequest(name="lh", network_name="net", is_lighthouse=True)

    def test_non_lighthouse_with_public_ip_raises(self):
        with pytest.raises(ValidationError):
            HostRequest(name="n", network_name="net", is_lighthouse=False, public_ip="1.2.3.4")

    def test_add_dns_record_defaults_true(self):
        req = HostRequest(name="node", network_name="net", is_lighthouse=False)
        assert req.add_dns_record is True


class TestStorageStore:
    def test_empty_defaults(self):
        store = StorageStore()
        assert store.pools == {} and store.volumes == {}

    def test_roundtrip_with_data(self):
        pool = PoolRecord(name="p1", path="/pools/p1", created_at="2025-01-01T00:00:00+00:00")
        vol = VolumeRecord(name="v1", pool_name="p1", host_path="/pools/p1/v1", created_at="2025-01-01T00:00:00+00:00")
        store = StorageStore(pools={"p1": pool}, volumes={"p1/v1": vol})
        restored = StorageStore.model_validate(store.model_dump())
        assert "p1" in restored.pools
        assert "p1/v1" in restored.volumes
