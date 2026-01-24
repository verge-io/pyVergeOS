"""Integration tests for connection."""

import pytest

from pyvergeos import VergeClient


@pytest.mark.integration
class TestLiveConnection:
    """Integration tests requiring live VergeOS."""

    def test_connect_and_get_version(self, live_client: VergeClient) -> None:
        """Test that we can connect and get version info."""
        assert live_client.is_connected
        assert live_client.version is not None

    def test_list_vms(self, live_client: VergeClient) -> None:
        """Test listing VMs."""
        vms = live_client.vms.list(limit=5)
        # Just verify it returns a list (may be empty)
        assert isinstance(vms, list)

    def test_list_networks(self, live_client: VergeClient) -> None:
        """Test listing networks."""
        networks = live_client.networks.list(limit=5)
        assert isinstance(networks, list)
