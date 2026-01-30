"""Integration tests for network proxy functionality.

These tests require a live VergeOS system with:
- An external network that can have proxy enabled
- At least one tenant available for proxy mapping

Set environment variables:
    VERGE_HOST=192.168.10.75
    VERGE_USERNAME=admin
    VERGE_PASSWORD=<password>
"""

from __future__ import annotations

import os

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.fixture
def live_client():
    """Create a live client for integration tests."""
    host = os.environ.get("VERGE_HOST")
    username = os.environ.get("VERGE_USERNAME")
    password = os.environ.get("VERGE_PASSWORD")

    if not all([host, username, password]):
        pytest.skip("Live VergeOS credentials not configured")

    client = VergeClient(
        host=host,
        username=username,
        password=password,
        verify_ssl=False,
    )

    yield client

    client.disconnect()


class TestVnetProxyIntegration:
    """Integration tests for network proxy functionality."""

    def test_list_networks_with_proxy_fields(self, live_client: VergeClient) -> None:
        """Test that networks include proxy-related fields."""
        networks = live_client.networks.list()
        assert len(networks) > 0

        # Check that proxy fields are available
        for network in networks:
            # These should be available even if proxy is not enabled
            _ = network.proxy_enabled
            _ = network.needs_proxy_apply

    def test_access_proxy_manager_from_network(self, live_client: VergeClient) -> None:
        """Test accessing proxy manager from a network."""
        networks = live_client.networks.list_external()
        if not networks:
            pytest.skip("No external networks available")

        network = networks[0]
        proxy_manager = network.proxy

        # Should be able to check if proxy exists
        exists = proxy_manager.exists()
        assert isinstance(exists, bool)

    def test_proxy_exists_on_external_network(self, live_client: VergeClient) -> None:
        """Test checking proxy existence on external network."""
        networks = live_client.networks.list_external()
        if not networks:
            pytest.skip("No external networks available")

        for network in networks:
            exists = network.proxy.exists()
            print(f"Network {network.name}: proxy_enabled={network.proxy_enabled}, exists={exists}")

            if exists:
                proxy = network.proxy.get()
                print(f"  Listen address: {proxy.listen_address}")
                print(f"  Default self: {proxy.default_self}")

                # List any tenant mappings
                tenants = proxy.tenants.list()
                print(f"  Tenant mappings: {len(tenants)}")
                for mapping in tenants:
                    print(f"    - {mapping.fqdn} -> {mapping.tenant_name}")

    def test_proxy_not_found_on_internal_network(self, live_client: VergeClient) -> None:
        """Test that internal networks typically don't have proxy."""
        networks = live_client.networks.list_internal()
        if not networks:
            pytest.skip("No internal networks available")

        # Find a network without proxy (most internal networks)
        for network in networks:
            if not network.proxy_enabled:
                with pytest.raises(NotFoundError):
                    network.proxy.get()
                return

        pytest.skip("All internal networks have proxy enabled (unexpected)")

    def test_list_tenants_for_potential_proxy_mapping(self, live_client: VergeClient) -> None:
        """Test listing tenants that could be mapped to proxy."""
        tenants = live_client.tenants.list()
        print(f"Available tenants for proxy mapping: {len(tenants)}")
        for tenant in tenants:
            print(f"  - {tenant.name} (key={tenant.key})")

    def test_proxy_get_or_create_workflow(self, live_client: VergeClient) -> None:
        """Test the get_or_create workflow for proxy.

        Note: This test only reads/checks existing configuration.
        It does not create or modify proxy settings to avoid
        disrupting the test environment.
        """
        networks = live_client.networks.list_external()
        if not networks:
            pytest.skip("No external networks available")

        network = networks[0]
        print(f"Testing proxy on network: {network.name}")

        # Check if proxy exists
        if network.proxy.exists():
            # Get existing proxy
            proxy = network.proxy.get_or_create()
            assert proxy is not None
            print(f"Existing proxy found: listen_address={proxy.listen_address}")
        else:
            print("No proxy configured on this network")
            print("Skipping get_or_create test to avoid modifying configuration")

    def test_proxy_tenant_list_workflow(self, live_client: VergeClient) -> None:
        """Test listing proxy tenant mappings."""
        networks = live_client.networks.list_external()
        if not networks:
            pytest.skip("No external networks available")

        for network in networks:
            if network.proxy.exists():
                proxy = network.proxy.get()
                tenants = proxy.tenants.list()
                print(f"Network {network.name} has {len(tenants)} proxy tenant mappings")

                for mapping in tenants:
                    # Test getting by different methods
                    by_key = proxy.tenants.get(key=mapping.key)
                    assert by_key.fqdn == mapping.fqdn

                    by_fqdn = proxy.tenants.get(fqdn=mapping.fqdn)
                    assert by_fqdn.key == mapping.key

                    by_tenant = proxy.tenants.get(tenant=mapping.tenant_key)
                    assert by_tenant.key == mapping.key

                    print(f"  Verified mapping: {mapping.fqdn}")
                return

        pytest.skip("No networks with proxy configured")


class TestVnetProxyCRUDOperations:
    """CRUD operation tests that modify configuration.

    These tests create and delete proxy configurations.
    Only run these if you understand the implications.
    """

    @pytest.mark.skip(reason="Modifies configuration - run manually if needed")
    def test_create_and_delete_proxy(self, live_client: VergeClient) -> None:
        """Test creating and deleting proxy configuration.

        WARNING: This test modifies network configuration.
        Only run manually after reviewing the code.
        """
        # Find an external network without proxy
        networks = live_client.networks.list_external()
        network = None
        for n in networks:
            if not n.proxy.exists():
                network = n
                break

        if not network:
            pytest.skip("No external network without proxy found")

        try:
            # Create proxy
            proxy = network.proxy.create(
                listen_address="0.0.0.0",
                default_self=True,
            )
            assert proxy.listen_address == "0.0.0.0"
            assert proxy.default_self is True

            # Update proxy
            updated = proxy.save(listen_address="192.168.1.1")
            assert updated.listen_address == "192.168.1.1"

        finally:
            # Cleanup - delete proxy
            if network.proxy.exists():
                network.proxy.delete()

    @pytest.mark.skip(reason="Modifies configuration - run manually if needed")
    def test_create_and_delete_tenant_mapping(self, live_client: VergeClient) -> None:
        """Test creating and deleting tenant mapping.

        WARNING: This test modifies proxy tenant configuration.
        Only run manually after reviewing the code.

        Note: Tenant mapping requires the tenant to NOT have a UI address.
        If tenant has a UI address, the API returns:
        "Tenant has a UI Address already set, this must be set to none for a FQDN to work"
        """
        # Find network with proxy
        networks = live_client.networks.list_external()
        proxy = None
        for n in networks:
            if n.proxy.exists():
                proxy = n.proxy.get()
                break

        if not proxy:
            pytest.skip("No network with proxy configured")

        # Find an available tenant
        tenants = live_client.tenants.list()
        if not tenants:
            pytest.skip("No tenants available")

        tenant = tenants[0]
        test_fqdn = f"pyvergeos-test-{tenant.key}.example.com"

        try:
            # Create mapping
            mapping = proxy.tenants.create(
                tenant=tenant.key,
                fqdn=test_fqdn,
            )
            assert mapping.fqdn == test_fqdn
            assert mapping.tenant_key == tenant.key

            # Update mapping
            new_fqdn = f"pyvergeos-test-updated-{tenant.key}.example.com"
            updated = mapping.save(fqdn=new_fqdn)
            assert updated.fqdn == new_fqdn

        finally:
            # Cleanup - delete mapping
            try:
                mapping_to_delete = proxy.tenants.get(fqdn=test_fqdn)
                mapping_to_delete.delete()
            except NotFoundError:
                pass  # Already cleaned up or different fqdn
            try:
                mapping_to_delete = proxy.tenants.get(
                    fqdn=f"pyvergeos-test-updated-{tenant.key}.example.com"
                )
                mapping_to_delete.delete()
            except NotFoundError:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
