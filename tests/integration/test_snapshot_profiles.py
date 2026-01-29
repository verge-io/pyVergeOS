"""Integration tests for Snapshot Profile operations.

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
def test_profile_name() -> str:
    """Generate a unique test profile name."""
    return unique_name("pyvergeos-profile")


@pytest.mark.integration
class TestSnapshotProfileListIntegration:
    """Integration tests for SnapshotProfileManager list operations."""

    def test_list_profiles(self, live_client: VergeClient) -> None:
        """Test listing profiles from live system."""
        profiles = live_client.snapshot_profiles.list()

        # Should return a list (may be empty)
        assert isinstance(profiles, list)

        # Each profile should have expected properties
        for profile in profiles:
            assert hasattr(profile, "key")
            assert hasattr(profile, "name")
            assert hasattr(profile, "description")
            assert hasattr(profile, "ignore_warnings")

    def test_list_profiles_with_limit(self, live_client: VergeClient) -> None:
        """Test listing profiles with limit."""
        profiles = live_client.snapshot_profiles.list(limit=1)

        assert isinstance(profiles, list)
        assert len(profiles) <= 1

    def test_list_profiles_include_periods(self, live_client: VergeClient) -> None:
        """Test listing profiles with periods included."""
        profiles = live_client.snapshot_profiles.list(include_periods=True)

        assert isinstance(profiles, list)
        for profile in profiles:
            # periods should be loaded (may be empty list)
            assert profile.periods is not None
            assert isinstance(profile.periods, list)


@pytest.mark.integration
class TestSnapshotProfileGetIntegration:
    """Integration tests for SnapshotProfileManager get operations."""

    def test_get_profile_by_key(self, live_client: VergeClient) -> None:
        """Test getting a profile by key."""
        # First get a profile from the list
        profiles = live_client.snapshot_profiles.list()
        if not profiles:
            pytest.skip("No snapshot profiles available for testing")

        profile = profiles[0]
        fetched = live_client.snapshot_profiles.get(profile.key)

        assert fetched.key == profile.key
        assert fetched.name == profile.name

    def test_get_profile_by_name(self, live_client: VergeClient) -> None:
        """Test getting a profile by name."""
        # First get a profile from the list
        profiles = live_client.snapshot_profiles.list()
        if not profiles:
            pytest.skip("No snapshot profiles available for testing")

        profile = profiles[0]
        fetched = live_client.snapshot_profiles.get(name=profile.name)

        assert fetched.key == profile.key
        assert fetched.name == profile.name

    def test_get_profile_with_periods(self, live_client: VergeClient) -> None:
        """Test getting a profile with periods included."""
        profiles = live_client.snapshot_profiles.list()
        if not profiles:
            pytest.skip("No snapshot profiles available for testing")

        profile = profiles[0]
        fetched = live_client.snapshot_profiles.get(
            profile.key, include_periods=True
        )

        assert fetched.periods is not None
        assert isinstance(fetched.periods, list)

    def test_get_profile_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent profile."""
        with pytest.raises(NotFoundError):
            live_client.snapshot_profiles.get(name="non-existent-profile-12345")


@pytest.mark.integration
class TestSnapshotProfileCRUDIntegration:
    """Integration tests for SnapshotProfile CRUD operations."""

    def test_create_and_delete_profile(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test creating and deleting a profile."""
        # Create profile
        profile = live_client.snapshot_profiles.create(
            name=test_profile_name,
            description="Integration test profile",
        )

        try:
            assert profile.name == test_profile_name
            assert profile.description == "Integration test profile"
            assert profile.key is not None

            # Verify it exists
            fetched = live_client.snapshot_profiles.get(profile.key)
            assert fetched.key == profile.key
        finally:
            # Cleanup
            live_client.snapshot_profiles.delete(profile.key)

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.snapshot_profiles.get(name=test_profile_name)

    def test_update_profile(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test updating a profile."""
        # Create profile
        profile = live_client.snapshot_profiles.create(
            name=test_profile_name,
            description="Original description",
        )

        try:
            # Update profile
            updated = live_client.snapshot_profiles.update(
                profile.key,
                description="Updated description",
            )

            assert updated.description == "Updated description"

            # Verify update persisted
            fetched = live_client.snapshot_profiles.get(profile.key)
            assert fetched.description == "Updated description"
        finally:
            # Cleanup
            live_client.snapshot_profiles.delete(profile.key)

    def test_profile_save_method(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test profile save() method."""
        # Create profile
        profile = live_client.snapshot_profiles.create(
            name=test_profile_name,
            description="Original",
        )

        try:
            # Use save method
            updated = profile.save(description="Saved description")
            assert updated.description == "Saved description"
        finally:
            # Cleanup
            live_client.snapshot_profiles.delete(profile.key)

    def test_profile_delete_method(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test profile delete() method."""
        # Create profile
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        # Delete using object method
        profile.delete()

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.snapshot_profiles.get(name=test_profile_name)


@pytest.mark.integration
class TestSnapshotProfilePeriodIntegration:
    """Integration tests for SnapshotProfilePeriod operations."""

    def test_list_periods(self, live_client: VergeClient) -> None:
        """Test listing periods for a profile."""
        profiles = live_client.snapshot_profiles.list()
        if not profiles:
            pytest.skip("No snapshot profiles available for testing")

        profile = profiles[0]
        periods = live_client.snapshot_profiles.periods(profile.key).list()

        assert isinstance(periods, list)
        for period in periods:
            assert hasattr(period, "key")
            assert hasattr(period, "name")
            assert hasattr(period, "frequency")
            assert hasattr(period, "retention_seconds")

    def test_create_and_delete_period(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test creating and deleting a period."""
        # Create profile
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            # Create period
            period = live_client.snapshot_profiles.periods(profile.key).create(
                name="Hourly",
                frequency="hourly",
                retention=86400,  # 1 day
            )

            assert period.name == "Hourly"
            assert period.frequency == "hourly"
            assert period.retention_seconds == 86400
            assert period.retention_display == "1d"

            # Verify it exists
            periods = live_client.snapshot_profiles.periods(profile.key).list()
            assert len(periods) == 1
            assert periods[0].name == "Hourly"

            # Delete period
            period.delete()

            # Verify deletion
            periods = live_client.snapshot_profiles.periods(profile.key).list()
            assert len(periods) == 0
        finally:
            # Cleanup profile
            live_client.snapshot_profiles.delete(profile.key)

    def test_add_period_via_profile(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test adding a period via profile.add_period()."""
        # Create profile
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            # Add period using profile method
            period = profile.add_period(
                name="Daily",
                frequency="daily",
                retention_seconds=604800,  # 7 days
                hour=2,
                minute=0,
            )

            assert period.name == "Daily"
            assert period.frequency == "daily"
            assert period.hour == 2
            assert period.minute == 0
            assert period.retention_display == "7d"

            # Verify via get_periods
            periods = profile.get_periods()
            assert len(periods) == 1
            assert periods[0].name == "Daily"
        finally:
            # Cleanup - delete periods first
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)

    def test_multiple_periods(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test creating multiple periods on a profile."""
        # Create profile
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            # Add multiple periods
            profile.add_period(
                name="Hourly",
                frequency="hourly",
                retention_seconds=86400,
            )
            profile.add_period(
                name="Daily",
                frequency="daily",
                retention_seconds=604800,
                hour=2,
            )
            profile.add_period(
                name="Weekly",
                frequency="weekly",
                retention_seconds=2592000,  # 30 days
                day_of_week="sun",
                hour=3,
            )

            # Verify all periods exist
            periods = profile.get_periods()
            assert len(periods) == 3
            period_names = {p.name for p in periods}
            assert period_names == {"Hourly", "Daily", "Weekly"}
        finally:
            # Cleanup
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)

    def test_update_period(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test updating a period."""
        # Create profile
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            # Create period
            period = profile.add_period(
                name="Daily",
                frequency="daily",
                retention_seconds=86400,
            )

            # Update period
            updated = live_client.snapshot_profiles.periods(profile.key).update(
                period.key,
                min_snapshots=5,
                quiesce=True,
            )

            assert updated.min_snapshots == 5
            assert updated.quiesce is True

            # Verify update persisted
            fetched = live_client.snapshot_profiles.periods(profile.key).get(
                period.key
            )
            assert fetched.min_snapshots == 5
        finally:
            # Cleanup
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)

    def test_period_save_method(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test period save() method."""
        # Create profile
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            # Create period
            period = profile.add_period(
                name="Hourly",
                frequency="hourly",
                retention_seconds=86400,
            )

            # Update using save method
            updated = period.save(min_snapshots=3)
            assert updated.min_snapshots == 3
        finally:
            # Cleanup
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)

    def test_get_period_by_name(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test getting a period by name."""
        # Create profile
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            # Create period
            profile.add_period(
                name="Daily",
                frequency="daily",
                retention_seconds=604800,
            )

            # Get by name
            fetched = live_client.snapshot_profiles.periods(profile.key).get(
                name="Daily"
            )
            assert fetched.name == "Daily"
        finally:
            # Cleanup
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)

    def test_period_not_found(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test getting a non-existent period."""
        # Create profile
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            with pytest.raises(NotFoundError):
                live_client.snapshot_profiles.periods(profile.key).get(
                    name="NonExistent"
                )
        finally:
            live_client.snapshot_profiles.delete(profile.key)


@pytest.mark.integration
class TestSnapshotProfilePeriodOptionsIntegration:
    """Integration tests for period schedule options."""

    def test_period_with_quiesce(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test creating a period with quiesce enabled."""
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            period = profile.add_period(
                name="Quiesced",
                frequency="daily",
                retention_seconds=86400,
                quiesce=True,
            )

            assert period.quiesce is True
        finally:
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)

    def test_period_with_skip_missed(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test creating a period with skip_missed enabled."""
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            period = profile.add_period(
                name="SkipMissed",
                frequency="hourly",
                retention_seconds=86400,
                skip_missed=True,
            )

            assert period.skip_missed is True
        finally:
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)

    def test_period_with_max_tier(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test creating a period with max_tier set."""
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            period = profile.add_period(
                name="Tier3",
                frequency="daily",
                retention_seconds=86400,
                max_tier=3,
            )

            assert period.max_tier == 3
        finally:
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)

    def test_period_with_min_snapshots(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test creating a period with min_snapshots set."""
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            period = profile.add_period(
                name="MinSnaps",
                frequency="daily",
                retention_seconds=86400,
                min_snapshots=5,
            )

            assert period.min_snapshots == 5
        finally:
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)

    def test_weekly_period_with_day(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test creating a weekly period with specific day."""
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            period = profile.add_period(
                name="WeeklySunday",
                frequency="weekly",
                retention_seconds=2592000,
                day_of_week="sun",
                hour=3,
                minute=30,
            )

            assert period.frequency == "weekly"
            assert period.day_of_week == "sun"
            assert period.day_of_week_display == "Sunday"
            assert period.hour == 3
            assert period.minute == 30
        finally:
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)

    def test_monthly_period(
        self, live_client: VergeClient, test_profile_name: str
    ) -> None:
        """Test creating a monthly period."""
        profile = live_client.snapshot_profiles.create(name=test_profile_name)

        try:
            period = profile.add_period(
                name="Monthly",
                frequency="monthly",
                retention_seconds=7776000,  # 90 days
                day_of_month=1,
                hour=4,
            )

            assert period.frequency == "monthly"
            assert period.day_of_month == 1
            assert period.hour == 4
        finally:
            for p in live_client.snapshot_profiles.periods(profile.key).list():
                p.delete()
            live_client.snapshot_profiles.delete(profile.key)
