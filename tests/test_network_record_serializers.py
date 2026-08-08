"""
Tests for NetworkRecord serializers.

TODO reference: datamodels.py:20 – "both serializers"

Covers:
- serialize_subnet: IPv6Network → str on model_dump / JSON output
- deserialize_subnet: str input → IPv6Network object on construction
"""
from __future__ import annotations

import ipaddress
import json

import pytest
from pydantic import ValidationError

from cep.datamodels import NetworkRecord


SUBNET_STR = "fd12:3456:789a:1::/64"
SUBNET_OBJ = ipaddress.IPv6Network(SUBNET_STR)


class TestSubnetSerializer:
    """serialize_subnet – IPv6Network is written out as a plain string."""

    def test_model_dump_subnet_is_string(self):
        rec = NetworkRecord(name="n", subnet=SUBNET_OBJ, hosts={}, dns=False)
        dumped = rec.model_dump()
        assert isinstance(dumped["subnet"], str), (
            "subnet must serialise to str, got " + type(dumped["subnet"]).__name__
        )

    def test_model_dump_subnet_value_matches(self):
        rec = NetworkRecord(name="n", subnet=SUBNET_OBJ, hosts={}, dns=False)
        assert rec.model_dump()["subnet"] == SUBNET_STR

    def test_model_dump_json_subnet_is_string(self):
        rec = NetworkRecord(name="n", subnet=SUBNET_OBJ, hosts={}, dns=False)
        parsed = json.loads(rec.model_dump_json())
        assert isinstance(parsed["subnet"], str)
        assert parsed["subnet"] == SUBNET_STR


class TestSubnetDeserializer:
    """deserialize_subnet – a str input is converted to IPv6Network."""

    def test_string_input_becomes_ipv6network(self):
        rec = NetworkRecord(name="n", subnet=SUBNET_STR, hosts={}, dns=False)
        assert isinstance(rec.subnet, ipaddress.IPv6Network)

    def test_ipv6network_input_is_preserved(self):
        rec = NetworkRecord(name="n", subnet=SUBNET_OBJ, hosts={}, dns=False)
        assert isinstance(rec.subnet, ipaddress.IPv6Network)
        assert rec.subnet == SUBNET_OBJ

    def test_roundtrip_through_model_dump(self):
        original = NetworkRecord(name="n", subnet=SUBNET_STR, hosts={}, dns=True)
        restored = NetworkRecord.model_validate(original.model_dump())
        assert restored.subnet == original.subnet

    def test_invalid_subnet_string_raises(self):
        with pytest.raises(ValidationError):
            NetworkRecord(name="n", subnet="not-a-valid-subnet", hosts={}, dns=False)

    def test_ipv4_subnet_is_rejected(self):
        with pytest.raises(ValidationError):
            NetworkRecord(name="n", subnet="192.168.1.0/24", hosts={}, dns=False)
