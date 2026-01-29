"""Unit tests for Snapshot Profile operations."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.snapshot_profiles import (
    DAY_OF_WEEK_DISPLAY,
    DAYS_OF_WEEK,
    FREQUENCIES,
    SnapshotProfile,
    SnapshotProfilePeriod,
)

# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_profile_data() -> dict[str, Any]:
    """Sample snapshot profile data."""
    return {
        "$key": 1,
        "name": "Test Profile",
        "description": "A test snapshot profile",
        "ignore_warnings": False,
    }


@pytest.fixture
def sample_period_data() -> dict[str, Any]:
    """Sample snapshot profile period data."""
    return {
        "$key": 10,
        "profile": 1,
        "name": "Daily",
        "frequency": "daily",
        "minute": 0,
        "hour": 2,
        "day_of_week": "any",
        "day_of_month": 0,
        "month": 0,
        "retention": 604800,  # 7 days
        "skip_missed": False,
        "max_tier": "1",
        "quiesce": False,
        "min_snapshots": 1,
        "immutable": False,
        "estimated_snapshot_count": 7,
    }


# =============================================================================
# SnapshotProfilePeriod Model Tests
# =============================================================================


class TestSnapshotProfilePeriod:
    """Unit tests for SnapshotProfilePeriod model."""

    def test_period_properties(
        self, mock_client: VergeClient, sample_period_data: dict[str, Any]
    ) -> None:
        """Test SnapshotProfilePeriod property accessors."""
        period = SnapshotProfilePeriod(
            sample_period_data, mock_client.snapshot_profiles.periods(1)
        )

        assert period.key == 10
        assert period.profile_key == 1
        assert period.name == "Daily"
        assert period.frequency == "daily"
        assert period.frequency_display == "Daily"
        assert period.minute == 0
        assert period.hour == 2
        assert period.day_of_week == "any"
        assert period.day_of_week_display == "Any Day"
        assert period.day_of_month == 0
        assert period.month == 0
        assert period.retention_seconds == 604800
        assert period.retention == timedelta(seconds=604800)
        assert period.retention_display == "7d"
        assert period.skip_missed is False
        assert period.max_tier == 1
        assert period.quiesce is False
        assert period.min_snapshots == 1
        assert period.is_immutable is False
        assert period.estimated_snapshot_count == 7

    def test_period_frequency_hourly(self, mock_client: VergeClient) -> None:
        """Test frequency_display for hourly period."""
        data = {"$key": 1, "profile": 1, "frequency": "hourly"}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.frequency_display == "Hourly"

    def test_period_frequency_weekly(self, mock_client: VergeClient) -> None:
        """Test frequency_display for weekly period."""
        data = {"$key": 1, "profile": 1, "frequency": "weekly"}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.frequency_display == "Weekly"

    def test_period_frequency_monthly(self, mock_client: VergeClient) -> None:
        """Test frequency_display for monthly period."""
        data = {"$key": 1, "profile": 1, "frequency": "monthly"}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.frequency_display == "Monthly"

    def test_period_frequency_yearly(self, mock_client: VergeClient) -> None:
        """Test frequency_display for yearly period."""
        data = {"$key": 1, "profile": 1, "frequency": "yearly"}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.frequency_display == "Yearly"

    def test_period_day_of_week_display_sunday(self, mock_client: VergeClient) -> None:
        """Test day_of_week_display for Sunday."""
        data = {"$key": 1, "profile": 1, "day_of_week": "sun"}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.day_of_week_display == "Sunday"

    def test_period_day_of_week_display_monday(self, mock_client: VergeClient) -> None:
        """Test day_of_week_display for Monday."""
        data = {"$key": 1, "profile": 1, "day_of_week": "mon"}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.day_of_week_display == "Monday"

    def test_period_day_of_week_display_friday(self, mock_client: VergeClient) -> None:
        """Test day_of_week_display for Friday."""
        data = {"$key": 1, "profile": 1, "day_of_week": "fri"}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.day_of_week_display == "Friday"

    def test_period_retention_display_days_and_hours(
        self, mock_client: VergeClient
    ) -> None:
        """Test retention_display with days and hours."""
        data = {"$key": 1, "profile": 1, "retention": 90000}  # 1 day 1 hour
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.retention_display == "1d 1h"

    def test_period_retention_display_hours_only(
        self, mock_client: VergeClient
    ) -> None:
        """Test retention_display with hours only."""
        data = {"$key": 1, "profile": 1, "retention": 7200}  # 2 hours
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.retention_display == "2h"

    def test_period_retention_display_none(self, mock_client: VergeClient) -> None:
        """Test retention_display with zero retention."""
        data = {"$key": 1, "profile": 1, "retention": 0}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.retention_display == "None"

    def test_period_immutable_true(self, mock_client: VergeClient) -> None:
        """Test is_immutable returns True when immutable."""
        data = {"$key": 1, "profile": 1, "immutable": True}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.is_immutable is True

    def test_period_immutable_default(self, mock_client: VergeClient) -> None:
        """Test is_immutable defaults to False."""
        data = {"$key": 1, "profile": 1}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.is_immutable is False

    def test_period_quiesce_true(self, mock_client: VergeClient) -> None:
        """Test quiesce returns True when enabled."""
        data = {"$key": 1, "profile": 1, "quiesce": True}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.quiesce is True

    def test_period_skip_missed_true(self, mock_client: VergeClient) -> None:
        """Test skip_missed returns True when enabled."""
        data = {"$key": 1, "profile": 1, "skip_missed": True}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.skip_missed is True

    def test_period_max_tier_default(self, mock_client: VergeClient) -> None:
        """Test max_tier defaults to 1."""
        data = {"$key": 1, "profile": 1}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.max_tier == 1

    def test_period_max_tier_string(self, mock_client: VergeClient) -> None:
        """Test max_tier handles string value."""
        data = {"$key": 1, "profile": 1, "max_tier": "3"}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.max_tier == 3

    def test_period_estimated_snapshot_count_none(
        self, mock_client: VergeClient
    ) -> None:
        """Test estimated_snapshot_count returns None when not set."""
        data = {"$key": 1, "profile": 1}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert period.estimated_snapshot_count is None

    def test_period_repr(self, mock_client: VergeClient) -> None:
        """Test period string representation."""
        data = {"$key": 1, "profile": 1, "name": "Daily", "frequency": "daily"}
        period = SnapshotProfilePeriod(
            data, mock_client.snapshot_profiles.periods(1)
        )
        assert repr(period) == "<SnapshotProfilePeriod key=1 name='Daily' frequency='Daily'>"


# =============================================================================
# SnapshotProfile Model Tests
# =============================================================================


class TestSnapshotProfile:
    """Unit tests for SnapshotProfile model."""

    def test_profile_properties(
        self, mock_client: VergeClient, sample_profile_data: dict[str, Any]
    ) -> None:
        """Test SnapshotProfile property accessors."""
        profile = SnapshotProfile(sample_profile_data, mock_client.snapshot_profiles)

        assert profile.key == 1
        assert profile.name == "Test Profile"
        assert profile.description == "A test snapshot profile"
        assert profile.ignore_warnings is False
        assert profile.periods is None

    def test_profile_with_periods(
        self, mock_client: VergeClient, sample_profile_data: dict[str, Any]
    ) -> None:
        """Test profile with periods loaded."""
        period1 = SnapshotProfilePeriod(
            {"$key": 1, "profile": 1, "name": "Hourly"},
            mock_client.snapshot_profiles.periods(1),
        )
        period2 = SnapshotProfilePeriod(
            {"$key": 2, "profile": 1, "name": "Daily"},
            mock_client.snapshot_profiles.periods(1),
        )

        profile = SnapshotProfile(
            sample_profile_data,
            mock_client.snapshot_profiles,
            periods=[period1, period2],
        )

        assert profile.periods is not None
        assert len(profile.periods) == 2
        assert profile.periods[0].name == "Hourly"
        assert profile.periods[1].name == "Daily"

    def test_profile_ignore_warnings_true(self, mock_client: VergeClient) -> None:
        """Test ignore_warnings returns True when set."""
        data = {"$key": 1, "name": "Test", "ignore_warnings": True}
        profile = SnapshotProfile(data, mock_client.snapshot_profiles)
        assert profile.ignore_warnings is True

    def test_profile_ignore_warnings_default(self, mock_client: VergeClient) -> None:
        """Test ignore_warnings defaults to False."""
        data = {"$key": 1, "name": "Test"}
        profile = SnapshotProfile(data, mock_client.snapshot_profiles)
        assert profile.ignore_warnings is False

    def test_profile_description_default(self, mock_client: VergeClient) -> None:
        """Test description defaults to empty string."""
        data = {"$key": 1, "name": "Test"}
        profile = SnapshotProfile(data, mock_client.snapshot_profiles)
        assert profile.description == ""

    def test_profile_repr(self, mock_client: VergeClient) -> None:
        """Test profile string representation."""
        data = {"$key": 1, "name": "Test Profile"}
        profile = SnapshotProfile(data, mock_client.snapshot_profiles)
        assert repr(profile) == "<SnapshotProfile key=1 name='Test Profile'>"


# =============================================================================
# SnapshotProfilePeriodManager Tests
# =============================================================================


class TestSnapshotProfilePeriodManager:
    """Unit tests for SnapshotProfilePeriodManager."""

    def test_list_periods(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing periods for a profile."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "profile": 1, "name": "Hourly", "frequency": "hourly"},
            {"$key": 2, "profile": 1, "name": "Daily", "frequency": "daily"},
        ]

        periods = mock_client.snapshot_profiles.periods(1).list()

        assert len(periods) == 2
        assert periods[0].name == "Hourly"
        assert periods[1].name == "Daily"

    def test_list_periods_empty(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing periods when none exist."""
        mock_session.request.return_value.json.return_value = []

        periods = mock_client.snapshot_profiles.periods(1).list()

        assert periods == []

    def test_get_period_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a period by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "profile": 1,
            "name": "Daily",
            "frequency": "daily",
        }

        period = mock_client.snapshot_profiles.periods(1).get(1)

        assert period.key == 1
        assert period.name == "Daily"

    def test_get_period_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a period by name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "profile": 1, "name": "Daily", "frequency": "daily"}
        ]

        period = mock_client.snapshot_profiles.periods(1).get(name="Daily")

        assert period.key == 1
        assert period.name == "Daily"

    def test_get_period_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a period that doesn't exist."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.snapshot_profiles.periods(1).get(name="NonExistent")

    def test_get_period_no_key_or_name(self, mock_client: VergeClient) -> None:
        """Test get period requires key or name."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.snapshot_profiles.periods(1).get()

    def test_create_period(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a period."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "profile": 1,
            "name": "Hourly",
            "frequency": "hourly",
            "retention": 86400,
        }

        period = mock_client.snapshot_profiles.periods(1).create(
            name="Hourly",
            frequency="hourly",
            retention=86400,
        )

        assert period.key == 1
        assert period.name == "Hourly"

    def test_create_period_invalid_frequency(self, mock_client: VergeClient) -> None:
        """Test create period with invalid frequency."""
        with pytest.raises(ValueError, match="Invalid frequency"):
            mock_client.snapshot_profiles.periods(1).create(
                name="Test",
                frequency="invalid",
                retention=86400,
            )

    def test_create_period_invalid_day_of_week(self, mock_client: VergeClient) -> None:
        """Test create period with invalid day_of_week."""
        with pytest.raises(ValueError, match="Invalid day_of_week"):
            mock_client.snapshot_profiles.periods(1).create(
                name="Test",
                frequency="weekly",
                retention=86400,
                day_of_week="invalid",
            )

    def test_create_period_invalid_minute(self, mock_client: VergeClient) -> None:
        """Test create period with invalid minute."""
        with pytest.raises(ValueError, match="minute must be between"):
            mock_client.snapshot_profiles.periods(1).create(
                name="Test",
                frequency="hourly",
                retention=86400,
                minute=60,
            )

    def test_create_period_invalid_hour(self, mock_client: VergeClient) -> None:
        """Test create period with invalid hour."""
        with pytest.raises(ValueError, match="hour must be between"):
            mock_client.snapshot_profiles.periods(1).create(
                name="Test",
                frequency="daily",
                retention=86400,
                hour=24,
            )

    def test_create_period_invalid_max_tier(self, mock_client: VergeClient) -> None:
        """Test create period with invalid max_tier."""
        with pytest.raises(ValueError, match="max_tier must be between"):
            mock_client.snapshot_profiles.periods(1).create(
                name="Test",
                frequency="daily",
                retention=86400,
                max_tier=6,
            )

    def test_create_period_negative_retention(self, mock_client: VergeClient) -> None:
        """Test create period with negative retention."""
        with pytest.raises(ValueError, match="retention must be non-negative"):
            mock_client.snapshot_profiles.periods(1).create(
                name="Test",
                frequency="daily",
                retention=-1,
            )

    def test_update_period(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating a period."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "profile": 1,
            "name": "Daily",
            "min_snapshots": 5,
        }

        period = mock_client.snapshot_profiles.periods(1).update(1, min_snapshots=5)

        assert period.min_snapshots == 5

    def test_update_period_invalid_frequency(self, mock_client: VergeClient) -> None:
        """Test update period with invalid frequency."""
        with pytest.raises(ValueError, match="Invalid frequency"):
            mock_client.snapshot_profiles.periods(1).update(1, frequency="invalid")

    def test_delete_period(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test deleting a period."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        # Should not raise
        mock_client.snapshot_profiles.periods(1).delete(1)


# =============================================================================
# SnapshotProfileManager Tests
# =============================================================================


class TestSnapshotProfileManager:
    """Unit tests for SnapshotProfileManager."""

    def test_list_profiles(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing profiles."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Profile 1"},
            {"$key": 2, "name": "Profile 2"},
        ]

        profiles = mock_client.snapshot_profiles.list()

        assert len(profiles) == 2
        assert profiles[0].name == "Profile 1"
        assert profiles[1].name == "Profile 2"

    def test_list_profiles_empty(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing profiles when none exist."""
        mock_session.request.return_value.json.return_value = []

        profiles = mock_client.snapshot_profiles.list()

        assert profiles == []

    def test_list_profiles_single(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing profiles returns single item as list."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Profile 1",
        }

        profiles = mock_client.snapshot_profiles.list()

        assert len(profiles) == 1
        assert profiles[0].name == "Profile 1"

    def test_get_profile_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a profile by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Profile",
        }

        profile = mock_client.snapshot_profiles.get(1)

        assert profile.key == 1
        assert profile.name == "Test Profile"

    def test_get_profile_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a profile by name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Test Profile"}
        ]

        profile = mock_client.snapshot_profiles.get(name="Test Profile")

        assert profile.key == 1
        assert profile.name == "Test Profile"

    def test_get_profile_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a profile that doesn't exist."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.snapshot_profiles.get(name="NonExistent")

    def test_get_profile_no_key_or_name(self, mock_client: VergeClient) -> None:
        """Test get profile requires key or name."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.snapshot_profiles.get()

    def test_create_profile(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a profile."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "New Profile",
            "description": "Test description",
        }

        profile = mock_client.snapshot_profiles.create(
            name="New Profile",
            description="Test description",
        )

        assert profile.key == 1
        assert profile.name == "New Profile"

    def test_create_profile_empty_name(self, mock_client: VergeClient) -> None:
        """Test create profile with empty name."""
        with pytest.raises(ValueError, match="name is required"):
            mock_client.snapshot_profiles.create(name="")

    def test_create_profile_with_ignore_warnings(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a profile with ignore_warnings."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "New Profile",
            "ignore_warnings": True,
        }

        profile = mock_client.snapshot_profiles.create(
            name="New Profile",
            ignore_warnings=True,
        )

        assert profile.ignore_warnings is True

    def test_update_profile(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating a profile."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Profile",
            "description": "Updated description",
        }

        profile = mock_client.snapshot_profiles.update(
            1, description="Updated description"
        )

        assert profile.description == "Updated description"

    def test_delete_profile(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test deleting a profile."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        # Should not raise
        mock_client.snapshot_profiles.delete(1)

    def test_periods_manager_caching(self, mock_client: VergeClient) -> None:
        """Test that period managers are cached."""
        manager1 = mock_client.snapshot_profiles.periods(1)
        manager2 = mock_client.snapshot_profiles.periods(1)
        manager3 = mock_client.snapshot_profiles.periods(2)

        assert manager1 is manager2
        assert manager1 is not manager3


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Test module constants."""

    def test_frequencies(self) -> None:
        """Test FREQUENCIES list."""
        assert "hourly" in FREQUENCIES
        assert "daily" in FREQUENCIES
        assert "weekly" in FREQUENCIES
        assert "monthly" in FREQUENCIES
        assert "yearly" in FREQUENCIES
        assert "custom" in FREQUENCIES

    def test_days_of_week(self) -> None:
        """Test DAYS_OF_WEEK list."""
        assert "sun" in DAYS_OF_WEEK
        assert "mon" in DAYS_OF_WEEK
        assert "tue" in DAYS_OF_WEEK
        assert "wed" in DAYS_OF_WEEK
        assert "thu" in DAYS_OF_WEEK
        assert "fri" in DAYS_OF_WEEK
        assert "sat" in DAYS_OF_WEEK
        assert "any" in DAYS_OF_WEEK

    def test_day_of_week_display(self) -> None:
        """Test DAY_OF_WEEK_DISPLAY mapping."""
        assert DAY_OF_WEEK_DISPLAY["sun"] == "Sunday"
        assert DAY_OF_WEEK_DISPLAY["mon"] == "Monday"
        assert DAY_OF_WEEK_DISPLAY["tue"] == "Tuesday"
        assert DAY_OF_WEEK_DISPLAY["wed"] == "Wednesday"
        assert DAY_OF_WEEK_DISPLAY["thu"] == "Thursday"
        assert DAY_OF_WEEK_DISPLAY["fri"] == "Friday"
        assert DAY_OF_WEEK_DISPLAY["sat"] == "Saturday"
        assert DAY_OF_WEEK_DISPLAY["any"] == "Any Day"
