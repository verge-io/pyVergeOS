"""Unit tests for Site operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, ValidationError
from pyvergeos.resources.sites import Site

# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_site_data() -> dict[str, Any]:
    """Sample site data."""
    return {
        "$key": 1,
        "name": "DR-Site",
        "description": "Disaster recovery site",
        "enabled": True,
        "url": "https://dr.example.com",
        "domain": "dr.example.com",
        "city": "New York",
        "country": "US",
        "timezone": "America/New_York",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "status": "idle",
        "status_info": "",
        "authentication_status": "authenticated",
        "config_cloud_snapshots": "send",
        "config_statistics": "disabled",
        "config_management": "disabled",
        "config_repair_server": "disabled",
        "vsan_host": "10.0.0.100",
        "vsan_port": 14201,
        "is_tenant": False,
        "incoming_syncs_enabled": True,
        "outgoing_syncs_enabled": True,
        "statistics_interval": 600,
        "statistics_retention": 3888000,
        "created": 1706054400,
        "modified": 1706140800,
        "creator": "admin",
    }


# =============================================================================
# Site Model Tests
# =============================================================================


class TestSite:
    """Unit tests for Site model."""

    def test_site_properties(
        self, mock_client: VergeClient, sample_site_data: dict[str, Any]
    ) -> None:
        """Test Site property accessors."""
        site = Site(sample_site_data, mock_client.sites)

        assert site.key == 1
        assert site.name == "DR-Site"
        assert site.description == "Disaster recovery site"
        assert site.is_enabled is True
        assert site.url == "https://dr.example.com"
        assert site.domain == "dr.example.com"
        assert site.city == "New York"
        assert site.country == "US"
        assert site.timezone == "America/New_York"
        assert site.latitude == 40.7128
        assert site.longitude == -74.0060
        assert site.status == "idle"
        assert site.status_info == ""
        assert site.authentication_status == "authenticated"
        assert site.is_authenticated is True
        assert site.config_cloud_snapshots == "send"
        assert site.config_statistics == "disabled"
        assert site.config_management == "disabled"
        assert site.config_repair_server == "disabled"
        assert site.vsan_host == "10.0.0.100"
        assert site.vsan_port == 14201
        assert site.is_tenant is False
        assert site.has_incoming_syncs is True
        assert site.has_outgoing_syncs is True
        assert site.statistics_interval == 600
        assert site.statistics_retention == 3888000
        assert site.creator == "admin"

    def test_site_created_at(
        self, mock_client: VergeClient, sample_site_data: dict[str, Any]
    ) -> None:
        """Test created_at timestamp parsing."""
        site = Site(sample_site_data, mock_client.sites)
        assert site.created_at is not None
        assert site.created_at.year == 2024

    def test_site_modified_at(
        self, mock_client: VergeClient, sample_site_data: dict[str, Any]
    ) -> None:
        """Test modified_at timestamp parsing."""
        site = Site(sample_site_data, mock_client.sites)
        assert site.modified_at is not None
        assert site.modified_at.year == 2024

    def test_site_enabled_false(self, mock_client: VergeClient) -> None:
        """Test is_enabled returns False when disabled."""
        data = {"$key": 1, "name": "Test", "enabled": False}
        site = Site(data, mock_client.sites)
        assert site.is_enabled is False

    def test_site_enabled_default(self, mock_client: VergeClient) -> None:
        """Test is_enabled defaults to False."""
        data = {"$key": 1, "name": "Test"}
        site = Site(data, mock_client.sites)
        assert site.is_enabled is False

    def test_site_status_error(self, mock_client: VergeClient) -> None:
        """Test status returns error."""
        data = {"$key": 1, "name": "Test", "status": "error"}
        site = Site(data, mock_client.sites)
        assert site.status == "error"

    def test_site_status_authenticating(self, mock_client: VergeClient) -> None:
        """Test status returns authenticating."""
        data = {"$key": 1, "name": "Test", "status": "authenticating"}
        site = Site(data, mock_client.sites)
        assert site.status == "authenticating"

    def test_site_status_syncing(self, mock_client: VergeClient) -> None:
        """Test status returns syncing."""
        data = {"$key": 1, "name": "Test", "status": "syncing"}
        site = Site(data, mock_client.sites)
        assert site.status == "syncing"

    def test_site_status_warning(self, mock_client: VergeClient) -> None:
        """Test status returns warning."""
        data = {"$key": 1, "name": "Test", "status": "warning"}
        site = Site(data, mock_client.sites)
        assert site.status == "warning"

    def test_site_authentication_status_unauthenticated(self, mock_client: VergeClient) -> None:
        """Test authentication_status returns unauthenticated."""
        data = {"$key": 1, "name": "Test", "authentication_status": "unauthenticated"}
        site = Site(data, mock_client.sites)
        assert site.authentication_status == "unauthenticated"
        assert site.is_authenticated is False

    def test_site_authentication_status_legacy(self, mock_client: VergeClient) -> None:
        """Test authentication_status returns legacy."""
        data = {"$key": 1, "name": "Test", "authentication_status": "legacy"}
        site = Site(data, mock_client.sites)
        assert site.authentication_status == "legacy"
        assert site.is_authenticated is False

    def test_site_config_cloud_snapshots_receive(self, mock_client: VergeClient) -> None:
        """Test config_cloud_snapshots returns receive."""
        data = {"$key": 1, "name": "Test", "config_cloud_snapshots": "receive"}
        site = Site(data, mock_client.sites)
        assert site.config_cloud_snapshots == "receive"

    def test_site_config_cloud_snapshots_both(self, mock_client: VergeClient) -> None:
        """Test config_cloud_snapshots returns both."""
        data = {"$key": 1, "name": "Test", "config_cloud_snapshots": "both"}
        site = Site(data, mock_client.sites)
        assert site.config_cloud_snapshots == "both"

    def test_site_config_management_manage(self, mock_client: VergeClient) -> None:
        """Test config_management returns manage."""
        data = {"$key": 1, "name": "Test", "config_management": "manage"}
        site = Site(data, mock_client.sites)
        assert site.config_management == "manage"

    def test_site_config_management_managed(self, mock_client: VergeClient) -> None:
        """Test config_management returns managed."""
        data = {"$key": 1, "name": "Test", "config_management": "managed"}
        site = Site(data, mock_client.sites)
        assert site.config_management == "managed"

    def test_site_is_tenant_true(self, mock_client: VergeClient) -> None:
        """Test is_tenant returns True."""
        data = {"$key": 1, "name": "Test", "is_tenant": True}
        site = Site(data, mock_client.sites)
        assert site.is_tenant is True

    def test_site_latitude_none(self, mock_client: VergeClient) -> None:
        """Test latitude returns None when not set."""
        data = {"$key": 1, "name": "Test"}
        site = Site(data, mock_client.sites)
        assert site.latitude is None

    def test_site_longitude_none(self, mock_client: VergeClient) -> None:
        """Test longitude returns None when not set."""
        data = {"$key": 1, "name": "Test"}
        site = Site(data, mock_client.sites)
        assert site.longitude is None

    def test_site_created_at_none(self, mock_client: VergeClient) -> None:
        """Test created_at returns None when not set."""
        data = {"$key": 1, "name": "Test"}
        site = Site(data, mock_client.sites)
        assert site.created_at is None

    def test_site_modified_at_none(self, mock_client: VergeClient) -> None:
        """Test modified_at returns None when not set."""
        data = {"$key": 1, "name": "Test"}
        site = Site(data, mock_client.sites)
        assert site.modified_at is None

    def test_site_repr(self, mock_client: VergeClient, sample_site_data: dict[str, Any]) -> None:
        """Test site string representation."""
        site = Site(sample_site_data, mock_client.sites)
        assert repr(site) == "<Site key=1 name='DR-Site' status='idle'>"

    def test_site_repr_error_status(self, mock_client: VergeClient) -> None:
        """Test site repr with error status."""
        data = {"$key": 1, "name": "Test Site", "status": "error"}
        site = Site(data, mock_client.sites)
        assert repr(site) == "<Site key=1 name='Test Site' status='error'>"


# =============================================================================
# SiteManager List Tests
# =============================================================================


class TestSiteManagerList:
    """Unit tests for SiteManager list operations."""

    def test_list_sites(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing sites."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Site 1", "status": "idle"},
            {"$key": 2, "name": "Site 2", "status": "error"},
        ]

        sites = mock_client.sites.list()

        assert len(sites) == 2
        assert sites[0].name == "Site 1"
        assert sites[1].name == "Site 2"

    def test_list_sites_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing sites when none exist."""
        mock_session.request.return_value.json.return_value = []

        sites = mock_client.sites.list()

        assert sites == []

    def test_list_sites_single(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing sites returns single item as list."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Site 1",
        }

        sites = mock_client.sites.list()

        assert len(sites) == 1
        assert sites[0].name == "Site 1"

    def test_list_sites_enabled_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing enabled sites."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Site 1", "enabled": True}
        ]

        sites = mock_client.sites.list(enabled=True)

        assert len(sites) == 1
        # Verify filter was applied
        call_args = mock_session.request.call_args
        assert "enabled eq true" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_sites_disabled_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing disabled sites."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Site 1", "enabled": False}
        ]

        sites = mock_client.sites.list(enabled=False)

        assert len(sites) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq false" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_sites_status_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing sites by status."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Site 1", "status": "error"}
        ]

        sites = mock_client.sites.list(status="error")

        assert len(sites) == 1
        call_args = mock_session.request.call_args
        assert "status eq 'error'" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_enabled(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_enabled convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Site 1", "enabled": True}
        ]

        sites = mock_client.sites.list_enabled()

        assert len(sites) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq true" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_disabled(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_disabled convenience method."""
        mock_session.request.return_value.json.return_value = []

        sites = mock_client.sites.list_disabled()

        assert sites == []
        call_args = mock_session.request.call_args
        assert "enabled eq false" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_by_status(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_by_status convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Site 1", "status": "idle"}
        ]

        sites = mock_client.sites.list_by_status("idle")

        assert len(sites) == 1
        call_args = mock_session.request.call_args
        assert "status eq 'idle'" in call_args.kwargs.get("params", {}).get("filter", "")


# =============================================================================
# SiteManager Get Tests
# =============================================================================


class TestSiteManagerGet:
    """Unit tests for SiteManager get operations."""

    def test_get_site_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a site by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
            "status": "idle",
        }

        site = mock_client.sites.get(1)

        assert site.key == 1
        assert site.name == "Test Site"

    def test_get_site_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a site by name."""
        mock_session.request.return_value.json.return_value = [{"$key": 1, "name": "Test Site"}]

        site = mock_client.sites.get(name="Test Site")

        assert site.key == 1
        assert site.name == "Test Site"

    def test_get_site_not_found_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a site that doesn't exist by key."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.status_code = 200
        mock_session.request.return_value.text = ""

        with pytest.raises(NotFoundError):
            mock_client.sites.get(999)

    def test_get_site_not_found_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a site that doesn't exist by name."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.sites.get(name="NonExistent")

    def test_get_site_no_key_or_name(self, mock_client: VergeClient) -> None:
        """Test get site requires key or name."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.sites.get()


# =============================================================================
# SiteManager Create Tests
# =============================================================================


class TestSiteManagerCreate:
    """Unit tests for SiteManager create operations."""

    def test_create_site(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a site."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "New Site",
            "url": "https://dr.example.com",
            "status": "authenticating",
        }

        site = mock_client.sites.create(
            name="New Site",
            url="https://dr.example.com",
            username="admin",
            password="secret",
        )

        assert site.key == 1
        assert site.name == "New Site"

    def test_create_site_with_options(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a site with all options."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Full Site",
            "config_cloud_snapshots": "send",
        }

        site = mock_client.sites.create(
            name="Full Site",
            url="https://dr.example.com",
            username="admin",
            password="secret",
            description="Test description",
            allow_insecure=True,
            config_cloud_snapshots="send",
            config_statistics="receive",
            config_management="manage",
            config_repair_server="both",
            auto_create_syncs=False,
            domain="dr.example.com",
            city="New York",
            country="US",
            timezone="America/New_York",
            request_url="https://main.example.com",
        )

        assert site.key == 1

    def test_create_site_invalid_url(self, mock_client: VergeClient) -> None:
        """Test create site with invalid URL."""
        with pytest.raises(ValidationError, match="URL must start with"):
            mock_client.sites.create(
                name="Test",
                url="ftp://invalid.com",
                username="admin",
                password="secret",
            )

    def test_create_site_invalid_config_cloud_snapshots(self, mock_client: VergeClient) -> None:
        """Test create site with invalid config_cloud_snapshots."""
        with pytest.raises(ValidationError, match="config_cloud_snapshots must be"):
            mock_client.sites.create(
                name="Test",
                url="https://dr.example.com",
                username="admin",
                password="secret",
                config_cloud_snapshots="invalid",
            )

    def test_create_site_invalid_config_statistics(self, mock_client: VergeClient) -> None:
        """Test create site with invalid config_statistics."""
        with pytest.raises(ValidationError, match="config_statistics must be"):
            mock_client.sites.create(
                name="Test",
                url="https://dr.example.com",
                username="admin",
                password="secret",
                config_statistics="invalid",
            )

    def test_create_site_invalid_config_management(self, mock_client: VergeClient) -> None:
        """Test create site with invalid config_management."""
        with pytest.raises(ValidationError, match="config_management must be"):
            mock_client.sites.create(
                name="Test",
                url="https://dr.example.com",
                username="admin",
                password="secret",
                config_management="invalid",
            )

    def test_create_site_invalid_config_repair_server(self, mock_client: VergeClient) -> None:
        """Test create site with invalid config_repair_server."""
        with pytest.raises(ValidationError, match="config_repair_server must be"):
            mock_client.sites.create(
                name="Test",
                url="https://dr.example.com",
                username="admin",
                password="secret",
                config_repair_server="invalid",
            )


# =============================================================================
# SiteManager Update Tests
# =============================================================================


class TestSiteManagerUpdate:
    """Unit tests for SiteManager update operations."""

    def test_update_site(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a site."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
            "description": "Updated description",
        }

        site = mock_client.sites.update(1, description="Updated description")

        assert site.description == "Updated description"

    def test_update_site_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating site name."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "New Name",
        }

        site = mock_client.sites.update(1, name="New Name")

        assert site.name == "New Name"

    def test_update_site_enabled(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating site enabled status."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
            "enabled": False,
        }

        site = mock_client.sites.update(1, enabled=False)

        assert site.is_enabled is False

    def test_update_site_no_changes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test update with no changes returns current site."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
        }

        site = mock_client.sites.update(1)

        assert site.key == 1


# =============================================================================
# SiteManager Delete Tests
# =============================================================================


class TestSiteManagerDelete:
    """Unit tests for SiteManager delete operations."""

    def test_delete_site(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a site."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        # Should not raise
        mock_client.sites.delete(1)


# =============================================================================
# SiteManager Enable/Disable Tests
# =============================================================================


class TestSiteManagerEnableDisable:
    """Unit tests for SiteManager enable/disable operations."""

    def test_enable_site(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test enabling a site."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
            "enabled": True,
        }

        site = mock_client.sites.enable(1)

        assert site.is_enabled is True

    def test_disable_site(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test disabling a site."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
            "enabled": False,
        }

        site = mock_client.sites.disable(1)

        assert site.is_enabled is False


# =============================================================================
# SiteManager Action Tests
# =============================================================================


class TestSiteManagerActions:
    """Unit tests for SiteManager action operations."""

    def test_reauthenticate(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test reauthenticating a site."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
            "authentication_status": "authenticated",
        }

        site = mock_client.sites.reauthenticate(1, "admin", "newpassword")

        assert site.key == 1

    def test_refresh_site(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test refreshing site data."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
        }

        site = mock_client.sites.refresh_site(1)

        assert site.key == 1

    def test_refresh_settings(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test refreshing site settings."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
        }

        site = mock_client.sites.refresh_settings(1)

        assert site.key == 1


# =============================================================================
# Site Object Method Tests
# =============================================================================


class TestSiteObjectMethods:
    """Unit tests for Site object methods."""

    def test_site_enable(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test Site.enable() method."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
            "enabled": True,
        }

        site = Site({"$key": 1, "name": "Test Site"}, mock_client.sites)
        enabled_site = site.enable()

        assert enabled_site.is_enabled is True

    def test_site_disable(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test Site.disable() method."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
            "enabled": False,
        }

        site = Site({"$key": 1, "name": "Test Site"}, mock_client.sites)
        disabled_site = site.disable()

        assert disabled_site.is_enabled is False

    def test_site_refresh(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test Site.refresh() method."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
            "status": "idle",
        }

        site = Site({"$key": 1, "name": "Test Site"}, mock_client.sites)
        refreshed_site = site.refresh()

        assert refreshed_site.key == 1

    def test_site_reauthenticate(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test Site.reauthenticate() method."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Site",
        }

        site = Site({"$key": 1, "name": "Test Site"}, mock_client.sites)
        reauthed_site = site.reauthenticate("admin", "newpassword")

        assert reauthed_site.key == 1

    def test_site_delete(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test Site.delete() method."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        site = Site({"$key": 1, "name": "Test Site"}, mock_client.sites)
        # Should not raise
        site.delete()
