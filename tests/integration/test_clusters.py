"""Integration tests for Cluster operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestClusterListIntegration:
    """Integration tests for ClusterManager.list()."""

    def test_list_clusters(self, live_client: VergeClient) -> None:
        """Test listing clusters from live system."""
        clusters = live_client.clusters.list()

        # Should have at least one cluster
        assert isinstance(clusters, list)
        if not clusters:
            pytest.skip("No clusters found on system")

        # Each cluster should have expected properties
        for cluster in clusters:
            assert hasattr(cluster, "key")
            assert hasattr(cluster, "name")
            assert cluster.key > 0
            assert cluster.name

    def test_list_clusters_with_limit(self, live_client: VergeClient) -> None:
        """Test listing clusters with limit."""
        clusters = live_client.clusters.list(limit=1)

        assert isinstance(clusters, list)
        assert len(clusters) <= 1

    def test_list_clusters_with_name_filter(self, live_client: VergeClient) -> None:
        """Test listing clusters filtered by name."""
        # First get all clusters
        all_clusters = live_client.clusters.list()
        if not all_clusters:
            pytest.skip("No clusters found on system")

        # Filter by the first cluster's name
        target_name = all_clusters[0].name
        filtered = live_client.clusters.list(name=target_name)

        assert len(filtered) >= 1
        assert all(c.name == target_name for c in filtered)

    def test_list_compute_clusters(self, live_client: VergeClient) -> None:
        """Test listing only compute clusters."""
        clusters = live_client.clusters.list(compute=True)

        assert isinstance(clusters, list)
        for cluster in clusters:
            assert cluster.is_compute is True


@pytest.mark.integration
class TestClusterGetIntegration:
    """Integration tests for ClusterManager.get()."""

    def test_get_cluster_by_key(self, live_client: VergeClient) -> None:
        """Test getting a cluster by key."""
        # First list to get a valid key
        clusters = live_client.clusters.list()
        if not clusters:
            pytest.skip("No clusters found on system")

        cluster = live_client.clusters.get(clusters[0].key)

        assert cluster.key == clusters[0].key
        assert cluster.name == clusters[0].name

    def test_get_cluster_by_name(self, live_client: VergeClient) -> None:
        """Test getting a cluster by name."""
        clusters = live_client.clusters.list()
        if not clusters:
            pytest.skip("No clusters found on system")

        cluster = live_client.clusters.get(name=clusters[0].name)

        assert cluster.name == clusters[0].name
        assert cluster.key == clusters[0].key

    def test_get_nonexistent_cluster(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent cluster."""
        with pytest.raises(NotFoundError):
            live_client.clusters.get(999999)


@pytest.mark.integration
class TestClusterPropertiesIntegration:
    """Integration tests for Cluster property accessors."""

    def test_cluster_properties(self, live_client: VergeClient) -> None:
        """Test cluster property accessors on live data."""
        clusters = live_client.clusters.list()
        if not clusters:
            pytest.skip("No clusters found on system")

        cluster = clusters[0]

        # Test all properties are accessible
        _ = cluster.key
        _ = cluster.name
        _ = cluster.description
        _ = cluster.is_enabled
        _ = cluster.is_compute
        _ = cluster.is_storage
        _ = cluster.default_cpu
        _ = cluster.status
        _ = cluster.status_raw
        _ = cluster.total_nodes
        _ = cluster.online_nodes
        _ = cluster.total_ram_mb
        _ = cluster.total_ram_gb
        _ = cluster.online_ram_mb
        _ = cluster.online_ram_gb
        _ = cluster.used_ram_mb
        _ = cluster.used_ram_gb
        _ = cluster.total_cores
        _ = cluster.online_cores
        _ = cluster.used_cores
        _ = cluster.running_machines

    def test_cluster_ram_usage(self, live_client: VergeClient) -> None:
        """Test cluster RAM usage properties are consistent."""
        clusters = live_client.clusters.list()
        if not clusters:
            pytest.skip("No clusters found on system")

        for cluster in clusters:
            # Used should be <= online
            if cluster.online_ram_mb > 0:
                assert cluster.used_ram_mb <= cluster.online_ram_mb
            # Online should be <= total
            assert cluster.online_ram_mb <= cluster.total_ram_mb

    def test_cluster_core_usage(self, live_client: VergeClient) -> None:
        """Test cluster core usage properties are consistent."""
        clusters = live_client.clusters.list()
        if not clusters:
            pytest.skip("No clusters found on system")

        for cluster in clusters:
            # Used should be <= online
            if cluster.online_cores > 0:
                assert cluster.used_cores <= cluster.online_cores
            # Online should be <= total
            assert cluster.online_cores <= cluster.total_cores


@pytest.mark.integration
class TestClusterVSANStatusIntegration:
    """Integration tests for ClusterManager.vsan_status()."""

    def test_vsan_status(self, live_client: VergeClient) -> None:
        """Test getting VSAN status from live system."""
        statuses = live_client.clusters.vsan_status()

        assert isinstance(statuses, list)
        if not statuses:
            pytest.skip("No VSAN status available")

        for status in statuses:
            # Check basic properties
            _ = status.cluster_name
            _ = status.health_status
            _ = status.total_nodes
            _ = status.online_nodes

    def test_vsan_status_with_tiers(self, live_client: VergeClient) -> None:
        """Test getting VSAN status with tier information."""
        statuses = live_client.clusters.vsan_status(include_tiers=True)

        assert isinstance(statuses, list)
        if not statuses:
            pytest.skip("No VSAN status available")

        for status in statuses:
            tiers = status.tiers
            assert isinstance(tiers, list)
