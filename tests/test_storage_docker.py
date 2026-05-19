"""Tests for cep.storage.docker – Pool and Volume filesystem operations."""
from __future__ import annotations

from pathlib import Path

import pytest

from cep.storage.docker import Pool, Volume, list_all_volumes, list_pools


class TestPool:
    def test_create_pool(self, storage_dir):
        pool = Pool("alpha")
        result = pool.create()
        assert result["name"] == "alpha"
        assert pool.exists()

    def test_create_duplicate_raises(self, storage_dir):
        Pool("alpha").create()
        with pytest.raises(ValueError, match="already exists"):
            Pool("alpha").create()

    def test_delete_pool(self, storage_dir):
        pool = Pool("alpha")
        pool.create()
        pool.delete()
        assert not pool.exists()

    def test_delete_nonexistent_raises(self, storage_dir):
        with pytest.raises(ValueError, match="does not exist"):
            Pool("ghost").delete()

    def test_delete_non_empty_raises(self, storage_dir):
        pool = Pool("alpha")
        pool.create()
        Volume("alpha", "vol1").create()
        with pytest.raises(ValueError, match="not empty"):
            pool.delete()

    def test_list_volumes_empty(self, storage_dir):
        pool = Pool("alpha")
        pool.create()
        assert pool.list_volumes() == []

    def test_list_volumes_with_volume(self, storage_dir):
        Pool("alpha").create()
        Volume("alpha", "vol1").create()
        assert "vol1" in Pool("alpha").list_volumes()

    def test_get_stats(self, storage_dir):
        pool = Pool("alpha")
        pool.create()
        stats = pool.get_stats()
        assert stats["name"] == "alpha"
        assert stats["volume_count"] == 0
        assert "total_size_bytes" in stats

    def test_get_stats_nonexistent_raises(self, storage_dir):
        with pytest.raises(ValueError):
            Pool("ghost").get_stats()


class TestVolume:
    def test_create_volume(self, storage_dir):
        Pool("alpha").create()
        vol = Volume("alpha", "vol1")
        result = vol.create()
        assert result["name"] == "vol1"
        assert result["pool_name"] == "alpha"
        assert Path(result["host_path"]).exists()

    def test_create_in_nonexistent_pool_raises(self, storage_dir):
        with pytest.raises(ValueError, match="does not exist"):
            Volume("ghost", "vol1").create()

    def test_create_duplicate_raises(self, storage_dir):
        Pool("alpha").create()
        Volume("alpha", "vol1").create()
        with pytest.raises(ValueError, match="already exists"):
            Volume("alpha", "vol1").create()

    def test_delete_volume(self, storage_dir):
        Pool("alpha").create()
        vol = Volume("alpha", "vol1")
        vol.create()
        vol.delete()
        assert not vol.path.exists()

    def test_delete_nonexistent_raises(self, storage_dir):
        Pool("alpha").create()
        with pytest.raises(ValueError, match="does not exist"):
            Volume("alpha", "ghost").delete()

    def test_info(self, storage_dir):
        Pool("alpha").create()
        Volume("alpha", "vol1").create()
        info = Volume("alpha", "vol1").info()
        assert info["name"] == "vol1"
        assert info["pool_name"] == "alpha"
        assert "total_size_bytes" in info
        assert "created_at" in info

    def test_info_nonexistent_raises(self, storage_dir):
        Pool("alpha").create()
        with pytest.raises(ValueError):
            Volume("alpha", "ghost").info()


class TestListFunctions:
    def test_list_pools_empty(self, storage_dir):
        assert list_pools() == []

    def test_list_pools(self, storage_dir):
        Pool("alpha").create()
        Pool("beta").create()
        names = {p["name"] for p in list_pools()}
        assert names == {"alpha", "beta"}

    def test_list_all_volumes_empty(self, storage_dir):
        assert list_all_volumes() == {}

    def test_list_all_volumes(self, storage_dir):
        Pool("alpha").create()
        Pool("beta").create()
        Volume("alpha", "v1").create()
        Volume("alpha", "v2").create()
        Volume("beta", "v3").create()
        result = list_all_volumes()
        assert set(result["alpha"]) == {"v1", "v2"}
        assert result["beta"] == ["v3"]
