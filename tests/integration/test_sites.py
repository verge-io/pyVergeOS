"""Integration tests for Site operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import uuid

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def unique_name(prefix: str = "pyvergeos-test") -> str:
    """Generate a unique name for test resources."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_site_name() -> str:
    """Generate a unique test site name."""
    return unique_name("pyvergeos-site")


@pytest.mark.integration
class TestSiteListIntegration:
    """Integration tests for SiteManager list operations."""

    def test_list_sites(self, live_client: VergeClient) -> None:
        """Test listing sites from live system."""
        sites = live_client.sites.list()

        # Should return a list (may be empty)
        assert isinstance(sites, list)

        # Each site should have expected properties
        for site in sites:
            assert hasattr(site, "key")
            assert hasattr(site, "name")
            assert hasattr(site, "url")
            assert hasattr(site, "status")
            assert hasattr(site, "is_enabled")
            assert hasattr(site, "authentication_status")

    def test_list_sites_with_limit(self, live_client: VergeClient) -> None:
        """Test listing sites with limit."""
        sites = live_client.sites.list(limit=1)

        assert isinstance(sites, list)
        assert len(sites) <= 1

    def test_list_enabled_sites(self, live_client: VergeClient) -> None:
        """Test listing enabled sites."""
        sites = live_client.sites.list_enabled()

        assert isinstance(sites, list)
        for site in sites:
            assert site.is_enabled is True

    def test_list_disabled_sites(self, live_client: VergeClient) -> None:
        """Test listing disabled sites."""
        sites = live_client.sites.list_disabled()

        assert isinstance(sites, list)
        for site in sites:
            assert site.is_enabled is False


@pytest.mark.integration
class TestSiteGetIntegration:
    """Integration tests for SiteManager get operations."""

    def test_get_site_by_key(self, live_client: VergeClient) -> None:
        """Test getting a site by key."""
        # First get a site from the list
        sites = live_client.sites.list()
        if not sites:
            pytest.skip("No sites available for testing")

        site = sites[0]
        fetched = live_client.sites.get(site.key)

        assert fetched.key == site.key
        assert fetched.name == site.name

    def test_get_site_by_name(self, live_client: VergeClient) -> None:
        """Test getting a site by name."""
        # First get a site from the list
        sites = live_client.sites.list()
        if not sites:
            pytest.skip("No sites available for testing")

        site = sites[0]
        fetched = live_client.sites.get(name=site.name)

        assert fetched.key == site.key
        assert fetched.name == site.name

    def test_get_site_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent site."""
        with pytest.raises(NotFoundError):
            live_client.sites.get(name="non-existent-site-12345")


@pytest.mark.integration
class TestSiteCRUDIntegration:
    """Integration tests for Site CRUD operations."""

    def test_create_and_delete_site(self, live_client: VergeClient, test_site_name: str) -> None:
        """Test creating and deleting a site.

        Note: This creates a site with a dummy URL that won't authenticate,
        but tests the create/delete API operations.
        """
        # Create site with dummy URL (will fail authentication but creation should work)
        site = live_client.sites.create(
            name=test_site_name,
            url="https://test.example.com",
            username="testuser",
            password="testpassword",
            description="Integration test site",
            allow_insecure=True,
            config_cloud_snapshots="disabled",
            auto_create_syncs=False,
        )

        try:
            assert site.name == test_site_name
            assert site.description == "Integration test site"
            assert site.key is not None
            assert site.url == "https://test.example.com"
            # Status will be authenticating or error since URL is fake
            assert site.status in ("authenticating", "error", "idle")

            # Verify it exists
            fetched = live_client.sites.get(site.key)
            assert fetched.key == site.key
            assert fetched.name == test_site_name
        finally:
            # Cleanup
            live_client.sites.delete(site.key)

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.sites.get(name=test_site_name)

    def test_update_site(self, live_client: VergeClient, test_site_name: str) -> None:
        """Test updating a site."""
        # Create site
        site = live_client.sites.create(
            name=test_site_name,
            url="https://test.example.com",
            username="testuser",
            password="testpassword",
            description="Original description",
            allow_insecure=True,
            auto_create_syncs=False,
        )

        try:
            # Update site
            updated = live_client.sites.update(
                site.key,
                description="Updated description",
            )

            assert updated.description == "Updated description"

            # Verify update persisted
            fetched = live_client.sites.get(site.key)
            assert fetched.description == "Updated description"
        finally:
            # Cleanup
            live_client.sites.delete(site.key)

    def test_enable_disable_site(self, live_client: VergeClient, test_site_name: str) -> None:
        """Test enabling and disabling a site."""
        # Create site (enabled by default)
        site = live_client.sites.create(
            name=test_site_name,
            url="https://test.example.com",
            username="testuser",
            password="testpassword",
            allow_insecure=True,
            auto_create_syncs=False,
        )

        try:
            assert site.is_enabled is True

            # Disable site
            disabled = live_client.sites.disable(site.key)
            assert disabled.is_enabled is False

            # Verify disable persisted
            fetched = live_client.sites.get(site.key)
            assert fetched.is_enabled is False

            # Re-enable site
            enabled = live_client.sites.enable(site.key)
            assert enabled.is_enabled is True

            # Verify enable persisted
            fetched = live_client.sites.get(site.key)
            assert fetched.is_enabled is True
        finally:
            # Cleanup
            live_client.sites.delete(site.key)


@pytest.mark.integration
class TestSiteObjectMethodsIntegration:
    """Integration tests for Site object methods."""

    def test_site_refresh_method(self, live_client: VergeClient) -> None:
        """Test Site.refresh() method."""
        sites = live_client.sites.list()
        if not sites:
            pytest.skip("No sites available for testing")

        site = sites[0]
        refreshed = site.refresh()

        assert refreshed.key == site.key
        assert refreshed.name == site.name

    def test_site_enable_disable_methods(
        self, live_client: VergeClient, test_site_name: str
    ) -> None:
        """Test Site.enable() and Site.disable() methods."""
        # Create site
        site = live_client.sites.create(
            name=test_site_name,
            url="https://test.example.com",
            username="testuser",
            password="testpassword",
            allow_insecure=True,
            auto_create_syncs=False,
        )

        try:
            # Use object methods
            disabled = site.disable()
            assert disabled.is_enabled is False

            enabled = disabled.enable()
            assert enabled.is_enabled is True
        finally:
            # Cleanup
            live_client.sites.delete(site.key)

    def test_site_delete_method(self, live_client: VergeClient, test_site_name: str) -> None:
        """Test Site.delete() method."""
        # Create site
        site = live_client.sites.create(
            name=test_site_name,
            url="https://test.example.com",
            username="testuser",
            password="testpassword",
            allow_insecure=True,
            auto_create_syncs=False,
        )

        # Delete using object method
        site.delete()

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.sites.get(name=test_site_name)


@pytest.mark.integration
class TestSiteConfigurationIntegration:
    """Integration tests for Site configuration options."""

    def test_site_with_cloud_snapshot_config(
        self, live_client: VergeClient, test_site_name: str
    ) -> None:
        """Test creating a site with cloud snapshot configuration."""
        site = live_client.sites.create(
            name=test_site_name,
            url="https://test.example.com",
            username="testuser",
            password="testpassword",
            allow_insecure=True,
            config_cloud_snapshots="send",
            auto_create_syncs=False,
        )

        try:
            assert site.config_cloud_snapshots == "send"

            # Verify persisted
            fetched = live_client.sites.get(site.key)
            assert fetched.config_cloud_snapshots == "send"
        finally:
            live_client.sites.delete(site.key)

    def test_site_with_statistics_config(
        self, live_client: VergeClient, test_site_name: str
    ) -> None:
        """Test creating a site with statistics configuration."""
        site = live_client.sites.create(
            name=test_site_name,
            url="https://test.example.com",
            username="testuser",
            password="testpassword",
            allow_insecure=True,
            config_statistics="receive",
            auto_create_syncs=False,
        )

        try:
            assert site.config_statistics == "receive"

            # Verify persisted
            fetched = live_client.sites.get(site.key)
            assert fetched.config_statistics == "receive"
        finally:
            live_client.sites.delete(site.key)

    def test_site_with_location_info(self, live_client: VergeClient, test_site_name: str) -> None:
        """Test creating a site with location information."""
        site = live_client.sites.create(
            name=test_site_name,
            url="https://test.example.com",
            username="testuser",
            password="testpassword",
            allow_insecure=True,
            city="New York",
            country="US",
            timezone="America/New_York",
            auto_create_syncs=False,
        )

        try:
            assert site.city == "New York"
            assert site.country == "US"
            assert site.timezone == "America/New_York"

            # Verify persisted
            fetched = live_client.sites.get(site.key)
            assert fetched.city == "New York"
            assert fetched.country == "US"
        finally:
            live_client.sites.delete(site.key)

    def test_update_site_config(self, live_client: VergeClient, test_site_name: str) -> None:
        """Test updating site configuration."""
        site = live_client.sites.create(
            name=test_site_name,
            url="https://test.example.com",
            username="testuser",
            password="testpassword",
            allow_insecure=True,
            config_cloud_snapshots="disabled",
            auto_create_syncs=False,
        )

        try:
            assert site.config_cloud_snapshots == "disabled"

            # Update configuration
            updated = live_client.sites.update(
                site.key,
                config_cloud_snapshots="send",
                config_statistics="receive",
            )

            assert updated.config_cloud_snapshots == "send"
            assert updated.config_statistics == "receive"
        finally:
            live_client.sites.delete(site.key)
