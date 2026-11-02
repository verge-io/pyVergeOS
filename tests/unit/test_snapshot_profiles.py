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
    SnapshotProfilePeriodManager,
    SnapshotProfilePeriodTag,
    SnapshotProfilePeriodTagManager,
    _rows_from_refs,
    _split_tag_keys,
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
        period = SnapshotProfilePeriod(sample_period_data, mock_client.snapshot_profiles.periods(1))

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
        assert period.max_tier == 1
        assert period.quiesce is False
        assert period.min_snapshots == 1
        assert period.is_immutable is False
        assert period.estimated_snapshot_count == 7

    def test_period_frequency_hourly(self, mock_client: VergeClient) -> None:
        """Test frequency_display for hourly period."""
        data = {"$key": 1, "profile": 1, "frequency": "hourly"}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.frequency_display == "Hourly"

    def test_period_frequency_weekly(self, mock_client: VergeClient) -> None:
        """Test frequency_display for weekly period."""
        data = {"$key": 1, "profile": 1, "frequency": "weekly"}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.frequency_display == "Weekly"

    def test_period_frequency_monthly(self, mock_client: VergeClient) -> None:
        """Test frequency_display for monthly period."""
        data = {"$key": 1, "profile": 1, "frequency": "monthly"}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.frequency_display == "Monthly"

    def test_period_frequency_yearly(self, mock_client: VergeClient) -> None:
        """Test frequency_display for yearly period."""
        data = {"$key": 1, "profile": 1, "frequency": "yearly"}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.frequency_display == "Yearly"

    def test_period_day_of_week_display_sunday(self, mock_client: VergeClient) -> None:
        """Test day_of_week_display for Sunday."""
        data = {"$key": 1, "profile": 1, "day_of_week": "sun"}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.day_of_week_display == "Sunday"

    def test_period_day_of_week_display_monday(self, mock_client: VergeClient) -> None:
        """Test day_of_week_display for Monday."""
        data = {"$key": 1, "profile": 1, "day_of_week": "mon"}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.day_of_week_display == "Monday"

    def test_period_day_of_week_display_friday(self, mock_client: VergeClient) -> None:
        """Test day_of_week_display for Friday."""
        data = {"$key": 1, "profile": 1, "day_of_week": "fri"}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.day_of_week_display == "Friday"

    def test_period_retention_display_days_and_hours(self, mock_client: VergeClient) -> None:
        """Test retention_display with days and hours."""
        data = {"$key": 1, "profile": 1, "retention": 90000}  # 1 day 1 hour
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.retention_display == "1d 1h"

    def test_period_retention_display_hours_only(self, mock_client: VergeClient) -> None:
        """Test retention_display with hours only."""
        data = {"$key": 1, "profile": 1, "retention": 7200}  # 2 hours
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.retention_display == "2h"

    def test_period_retention_display_none(self, mock_client: VergeClient) -> None:
        """Test retention_display with zero retention."""
        data = {"$key": 1, "profile": 1, "retention": 0}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.retention_display == "None"

    def test_period_immutable_true(self, mock_client: VergeClient) -> None:
        """Test is_immutable returns True when immutable."""
        data = {"$key": 1, "profile": 1, "immutable": True}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.is_immutable is True

    def test_period_immutable_default(self, mock_client: VergeClient) -> None:
        """Test is_immutable defaults to False."""
        data = {"$key": 1, "profile": 1}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.is_immutable is False

    def test_period_quiesce_true(self, mock_client: VergeClient) -> None:
        """Test quiesce returns True when enabled."""
        data = {"$key": 1, "profile": 1, "quiesce": True}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.quiesce is True

    def test_period_has_no_skip_missed(self, mock_client: VergeClient) -> None:
        """skip_missed is not a period column and must not default to False (#139)."""
        data = {"$key": 1, "profile": 1}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        with pytest.raises(AttributeError):
            _ = period.skip_missed

    def test_period_max_tier_default(self, mock_client: VergeClient) -> None:
        """Test max_tier defaults to 1."""
        data = {"$key": 1, "profile": 1}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.max_tier == 1

    def test_period_max_tier_string(self, mock_client: VergeClient) -> None:
        """Test max_tier handles string value."""
        data = {"$key": 1, "profile": 1, "max_tier": "3"}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.max_tier == 3

    def test_period_estimated_snapshot_count_none(self, mock_client: VergeClient) -> None:
        """Test estimated_snapshot_count returns None when not set."""
        data = {"$key": 1, "profile": 1}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
        assert period.estimated_snapshot_count is None

    def test_period_repr(self, mock_client: VergeClient) -> None:
        """Test period string representation."""
        data = {"$key": 1, "profile": 1, "name": "Daily", "frequency": "daily"}
        period = SnapshotProfilePeriod(data, mock_client.snapshot_profiles.periods(1))
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

    def test_add_period_rejects_skip_missed(
        self, mock_client: VergeClient, sample_profile_data: dict[str, Any]
    ) -> None:
        """add_period() must not offer skip_missed (#139)."""
        profile = SnapshotProfile(sample_profile_data, mock_client.snapshot_profiles)
        with pytest.raises(TypeError, match="skip_missed"):
            profile.add_period(
                name="Hourly",
                frequency="hourly",
                retention_seconds=86400,
                skip_missed=True,
            )


# =============================================================================
# SnapshotProfilePeriodManager Tests
# =============================================================================


class TestSnapshotProfilePeriodManager:
    """Unit tests for SnapshotProfilePeriodManager."""

    def test_list_periods(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing periods for a profile."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "profile": 1, "name": "Hourly", "frequency": "hourly"},
            {"$key": 2, "profile": 1, "name": "Daily", "frequency": "daily"},
        ]

        periods = mock_client.snapshot_profiles.periods(1).list()

        assert len(periods) == 2
        assert periods[0].name == "Hourly"
        assert periods[1].name == "Daily"

    def test_list_periods_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing periods when none exist."""
        mock_session.request.return_value.json.return_value = []

        periods = mock_client.snapshot_profiles.periods(1).list()

        assert periods == []

    def test_get_period_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

    def test_get_period_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a period by name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "profile": 1, "name": "Daily", "frequency": "daily"}
        ]

        period = mock_client.snapshot_profiles.periods(1).get(name="Daily")

        assert period.key == 1
        assert period.name == "Daily"

    def test_get_period_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a period that doesn't exist."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.snapshot_profiles.periods(1).get(name="NonExistent")

    def test_get_period_no_key_or_name(self, mock_client: VergeClient) -> None:
        """Test get period requires key or name."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.snapshot_profiles.periods(1).get()

    def test_create_period(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

    def test_create_period_omits_skip_missed(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Create must not send skip_missed; the column does not exist (#139)."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "profile": 1,
            "name": "Hourly",
            "frequency": "hourly",
            "retention": 86400,
        }

        mock_client.snapshot_profiles.periods(1).create(
            name="Hourly",
            frequency="hourly",
            retention=86400,
        )

        post = next(
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        )
        assert post.kwargs.get("json") == {
            "profile": 1,
            "name": "Hourly",
            "frequency": "hourly",
            "retention": 86400,
            "minute": 0,
            "hour": 0,
            "day_of_week": "any",
            "day_of_month": 0,
            "month": 0,
            "max_tier": "1",
            "quiesce": False,
            "min_snapshots": 1,
            "immutable": False,
        }

    def test_create_period_rejects_skip_missed(self, mock_client: VergeClient) -> None:
        """skip_missed is not a create parameter (#139)."""
        with pytest.raises(TypeError, match="skip_missed"):
            mock_client.snapshot_profiles.periods(1).create(  # type: ignore[call-arg]
                name="Test",
                frequency="hourly",
                retention=86400,
                skip_missed=True,
            )

    def test_list_periods_does_not_request_skip_missed(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """The default projection must not ask for a column that does not exist (#139)."""
        mock_session.request.return_value.json.return_value = []

        mock_client.snapshot_profiles.periods(1).list()

        params = mock_session.request.call_args.kwargs.get("params", {})
        fields = str(params.get("fields", ""))
        assert "skip_missed" not in fields.split(",")

    def test_update_period(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

    def test_update_period_rejects_skip_missed(self, mock_client: VergeClient) -> None:
        """update() must not forward skip_missed for the server to discard (#139)."""
        with pytest.raises(ValueError, match="skip_missed"):
            mock_client.snapshot_profiles.periods(1).update(1, skip_missed=True)

    def test_save_rejects_skip_missed(
        self, mock_client: VergeClient, sample_period_data: dict[str, Any]
    ) -> None:
        """save() rejects skip_missed the same way update() does (#139)."""
        period = SnapshotProfilePeriod(sample_period_data, mock_client.snapshot_profiles.periods(1))
        with pytest.raises(ValueError, match="skip_missed"):
            period.save(skip_missed=True)

    def test_delete_period(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

    def test_list_profiles(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing profiles."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Profile 1"},
            {"$key": 2, "name": "Profile 2"},
        ]

        profiles = mock_client.snapshot_profiles.list()

        assert len(profiles) == 2
        assert profiles[0].name == "Profile 1"
        assert profiles[1].name == "Profile 2"

    def test_list_profiles_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing profiles when none exist."""
        mock_session.request.return_value.json.return_value = []

        profiles = mock_client.snapshot_profiles.list()

        assert profiles == []

    def test_list_profiles_single(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing profiles returns single item as list."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Profile 1",
        }

        profiles = mock_client.snapshot_profiles.list()

        assert len(profiles) == 1
        assert profiles[0].name == "Profile 1"

    def test_get_profile_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a profile by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Profile",
        }

        profile = mock_client.snapshot_profiles.get(1)

        assert profile.key == 1
        assert profile.name == "Test Profile"

    def test_get_profile_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a profile by name."""
        mock_session.request.return_value.json.return_value = [{"$key": 1, "name": "Test Profile"}]

        profile = mock_client.snapshot_profiles.get(name="Test Profile")

        assert profile.key == 1
        assert profile.name == "Test Profile"

    def test_get_profile_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a profile that doesn't exist."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.snapshot_profiles.get(name="NonExistent")

    def test_get_profile_no_key_or_name(self, mock_client: VergeClient) -> None:
        """Test get profile requires key or name."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.snapshot_profiles.get()

    def test_create_profile(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

    def test_update_profile(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a profile."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Profile",
            "description": "Updated description",
        }

        profile = mock_client.snapshot_profiles.update(1, description="Updated description")

        assert profile.description == "Updated description"

    def test_delete_profile(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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


def _post_json(mock_session: MagicMock) -> dict[str, Any]:
    for call in mock_session.request.call_args_list:
        if call.kwargs.get("method") == "POST":
            body = call.kwargs.get("json")
            if isinstance(body, dict):
                return body
    raise AssertionError("no POST body")


def _put_json(mock_session: MagicMock) -> dict[str, Any]:
    for call in mock_session.request.call_args_list:
        if call.kwargs.get("method") == "PUT":
            body = call.kwargs.get("json")
            if isinstance(body, dict):
                return body
    raise AssertionError("no PUT body")


class TestPeriodTagScope:
    """Period tag columns, measured on a stored row (issue #199)."""

    def test_tag_properties(self, mock_client: VergeClient) -> None:
        period = SnapshotProfilePeriod(
            {
                "$key": 10,
                "profile": 1,
                "type": "partial_include",
                "partial_tags": "3,4",
                "quiesce_tags": "3",
                "private": True,
            },
            mock_client.snapshot_profiles.periods(1),
        )
        assert period.snapshot_type == "partial_include"
        assert period.is_partial is True
        assert period.partial_tags == "3,4"
        assert period.partial_tag_keys == [3, 4]
        assert period.quiesce_tags == "3"
        assert period.quiesce_tag_keys == [3]
        assert period.is_private is True

    def test_missing_type_reads_as_full(self, mock_client: VergeClient) -> None:
        period = SnapshotProfilePeriod(
            {"$key": 10, "profile": 1},
            mock_client.snapshot_profiles.periods(1),
        )
        assert period.snapshot_type == "full"
        assert period.is_partial is False
        assert period.partial_tag_keys == []
        assert period.quiesce_tag_keys == []
        assert period.is_private is False

    def test_list_requests_the_measured_tag_columns(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = []
        mock_client.snapshot_profiles.periods(1).list()
        fields = str(mock_session.request.call_args.kwargs["params"]["fields"]).split(",")
        for name in ("type", "partial_tags", "quiesce_tags", "private"):
            assert name in fields
        assert "site_sync_refs" not in fields
        assert "skip_missed" not in fields

    def test_create_include_tags(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 10,
            "profile": 1,
            "name": "DB",
            "type": "partial_include",
            "partial_tags": "3",
            "quiesce_tags": "3",
        }
        period = mock_client.snapshot_profiles.periods(1).create(
            name="DB",
            frequency="hourly",
            retention=3600,
            include_tags=[3],
            quiesce_tags=[3],
        )
        body = _post_json(mock_session)
        assert body["type"] == "partial_include"
        assert body["partial_tags"] == "3"
        assert body["quiesce_tags"] == "3"
        assert period.snapshot_type == "partial_include"
        assert period.partial_tag_keys == [3]

    def test_create_exclude_tags(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 11,
            "profile": 1,
            "name": "Rest",
            "type": "partial_exclude",
            "partial_tags": "1,2",
        }
        mock_client.snapshot_profiles.periods(1).create(
            name="Rest",
            frequency="daily",
            retention=86400,
            exclude_tags=[1, 2],
        )
        body = _post_json(mock_session)
        assert body["type"] == "partial_exclude"
        assert body["partial_tags"] == "1,2"
        assert "quiesce_tags" not in body

    def test_single_tag_string_is_not_split(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 12,
            "profile": 1,
            "name": "One",
            "type": "partial_include",
            "partial_tags": "3",
        }
        mock_client.snapshot_profiles.periods(1).create(
            name="One",
            frequency="daily",
            retention=86400,
            include_tags="3",
        )
        assert _post_json(mock_session)["partial_tags"] == "3"

    def test_include_and_exclude_rejected(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="mutually exclusive"):
            mock_client.snapshot_profiles.periods(1).create(
                name="Bad",
                frequency="daily",
                retention=86400,
                include_tags=[1],
                exclude_tags=[2],
            )

    def test_quiesce_without_partial_rejected(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="only to a partial"):
            mock_client.snapshot_profiles.periods(1).create(
                name="Bad",
                frequency="daily",
                retention=86400,
                quiesce_tags=[1],
            )

    def test_empty_include_rejected(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="at least one"):
            mock_client.snapshot_profiles.periods(1).create(
                name="Bad",
                frequency="daily",
                retention=86400,
                include_tags=[],
            )

    def test_empty_quiesce_on_create_is_omitted(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 13,
            "profile": 1,
            "name": "NQ",
            "type": "partial_include",
            "partial_tags": "3",
        }
        mock_client.snapshot_profiles.periods(1).create(
            name="NQ",
            frequency="daily",
            retention=86400,
            include_tags=[3],
            quiesce_tags=[],
        )
        assert "quiesce_tags" not in _post_json(mock_session)

    def test_name_is_resolved(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        def respond(*_args: Any, **kwargs: Any) -> MagicMock:
            response = MagicMock()
            response.status_code = 200
            response.text = "{}"
            url = str(kwargs.get("url", ""))
            if kwargs.get("method") == "GET" and url.rstrip("/").endswith("/tags"):
                response.json.return_value = [{"$key": 3}]
            else:
                response.json.return_value = {
                    "$key": 14,
                    "profile": 1,
                    "name": "Named",
                    "type": "partial_include",
                    "partial_tags": "3",
                }
            return response

        mock_session.request.side_effect = respond
        mock_client.snapshot_profiles.periods(1).create(
            name="Named",
            frequency="daily",
            retention=86400,
            include_tags=["DB"],
        )
        assert _post_json(mock_session)["partial_tags"] == "3"

    def test_update_clears_with_full(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 10,
            "profile": 1,
            "type": "full",
            "partial_tags": "",
            "quiesce_tags": "",
        }
        period = mock_client.snapshot_profiles.periods(1).update(10, snapshot_type="full")
        body = _put_json(mock_session)
        assert body["type"] == "full"
        assert body["partial_tags"] == ""
        assert body["quiesce_tags"] == ""
        assert period.snapshot_type == "full"

    def test_raw_type_full_clears_tag_columns(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 10,
            "profile": 1,
            "type": "full",
        }
        mock_client.snapshot_profiles.periods(1).update(10, type="full")
        body = _put_json(mock_session)
        assert body["partial_tags"] == ""
        assert body["quiesce_tags"] == ""

    def test_update_quiesce_on_existing_partial(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 10,
            "profile": 1,
            "type": "partial_include",
            "partial_tags": "3",
            "quiesce_tags": "3",
        }
        mock_client.snapshot_profiles.periods(1).update(10, quiesce_tags=[3])
        assert _put_json(mock_session)["quiesce_tags"] == "3"

    def test_update_quiesce_on_full_period_rejected(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 10,
            "profile": 1,
            "type": "full",
        }
        with pytest.raises(ValueError, match="only to a partial"):
            mock_client.snapshot_profiles.periods(1).update(10, quiesce_tags=[3])

    def test_empty_quiesce_on_update_clears(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 10,
            "profile": 1,
            "type": "partial_include",
            "quiesce_tags": "",
        }
        mock_client.snapshot_profiles.periods(1).update(10, quiesce_tags=[])
        assert _put_json(mock_session)["quiesce_tags"] == ""

    def test_snapshot_type_partial_is_rejected(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="only accepts 'full'"):
            mock_client.snapshot_profiles.periods(1).update(10, snapshot_type="partial_include")

    def test_full_plus_include_rejected(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="cannot be combined"):
            mock_client.snapshot_profiles.periods(1).update(
                10, snapshot_type="full", include_tags=[1]
            )

    def test_raw_column_and_convenience_rejected(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 10,
            "profile": 1,
            "type": "partial_exclude",
        }
        with pytest.raises(ValueError, match="not both"):
            mock_client.snapshot_profiles.periods(1).update(
                10, exclude_tags=[2], type="partial_exclude"
            )

    def test_invalid_type_rejected(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="Invalid type"):
            mock_client.snapshot_profiles.periods(1).update(10, type="Partial")

    def test_save_accepts_include_tags(
        self, mock_client: VergeClient, mock_session: MagicMock, sample_period_data: dict[str, Any]
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            **sample_period_data,
            "type": "partial_include",
            "partial_tags": "8",
        }
        period = SnapshotProfilePeriod(sample_period_data, mock_client.snapshot_profiles.periods(1))
        period.save(include_tags=[8])
        assert _put_json(mock_session)["partial_tags"] == "8"

    def test_assigned_include_tags_is_rejected(
        self, mock_client: VergeClient, sample_period_data: dict[str, Any]
    ) -> None:
        period = SnapshotProfilePeriod(sample_period_data, mock_client.snapshot_profiles.periods(1))
        period.include_tags = [1]
        with pytest.raises(ValueError, match="not a snapshot profile period column"):
            period.save()

    def test_assigned_partial_tags_list_is_coerced(
        self, mock_client: VergeClient, mock_session: MagicMock, sample_period_data: dict[str, Any]
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            **sample_period_data,
            "partial_tags": "4,5",
        }
        period = SnapshotProfilePeriod(sample_period_data, mock_client.snapshot_profiles.periods(1))
        period.partial_tags = [4, 5]
        period.save()
        assert _put_json(mock_session)["partial_tags"] == "4,5"

    def test_add_period_forwards_tags(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Profile",
            "description": "",
            "ignore_warnings": False,
        }
        profile = mock_client.snapshot_profiles.get(1)
        mock_session.request.return_value.json.return_value = {
            "$key": 20,
            "profile": 1,
            "name": "Hourly",
            "type": "partial_exclude",
            "partial_tags": "9",
        }
        profile.add_period(
            name="Hourly",
            frequency="hourly",
            retention_seconds=3600,
            exclude_tags=[9],
        )
        assert _post_json(mock_session)["type"] == "partial_exclude"

    def test_ambiguous_name_raises(self) -> None:
        client = MagicMock()
        client._request.return_value = [{"$key": 1}, {"$key": 2}]
        manager = SnapshotProfilePeriodManager(client, 1)
        with pytest.raises(ValueError, match="ambiguous"):
            manager._period_tag_body(
                include_tags=["gold"],
                exclude_tags=None,
                quiesce_tags=None,
                snapshot_type=None,
                current_type=None,
                clear_empty_quiesce=False,
            )


class TestRefParsing:
    def test_split_keys(self) -> None:
        assert _split_tag_keys("1, 2,x,") == [1, 2]
        assert _split_tag_keys(None) == []
        assert _split_tag_keys(False) == []

    def test_rows_from_expanded_refs(self) -> None:
        assert _rows_from_refs([{"$key": 4, "kept": 1}]) == [{"$key": 4, "kept": 1}]

    def test_rows_from_keys(self) -> None:
        assert _rows_from_refs([7, "8"]) == [{"$key": 7}, {"$key": 8}]
        assert _rows_from_refs("7,8") == [{"$key": 7}, {"$key": 8}]
        assert _rows_from_refs({"$key": 7}) == [{"$key": 7}]

    def test_a_count_is_not_a_row(self) -> None:
        assert _rows_from_refs(0) == []
        assert _rows_from_refs(3) == []
        assert _rows_from_refs(None) == []
        assert _rows_from_refs(True) == []
        assert _rows_from_refs("nope") == []


class TestSnapshotProfilePeriodTags:
    def test_scoped_list_filters_by_period(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "snapshot_profile_period": 10, "refs": 0}
        ]
        rows = mock_client.snapshot_profiles.periods(1).period_tags(10).list()
        params = mock_session.request.call_args.kwargs["params"]
        assert params["filter"] == "snapshot_profile_period eq 10"
        assert rows[0].period_key == 10
        assert rows[0].refs == 0

    def test_client_list(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = []
        assert mock_client.snapshot_profile_period_tags.list() == []
        fields = mock_session.request.call_args.kwargs["params"]["fields"]
        assert "snapshot_profile_period" in fields
        assert "refs" in fields

    def test_get_by_name_refused(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="no name column"):
            mock_client.snapshot_profile_period_tags.get(name="daily")

    def test_get_refuses_another_period(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 5,
            "snapshot_profile_period": 99,
        }
        with pytest.raises(NotFoundError, match="does not belong"):
            mock_client.snapshot_profiles.periods(1).period_tags(10).get(5)

    def test_create_scoped(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 6,
            "snapshot_profile_period": 10,
            "refs": [],
        }
        row = mock_client.snapshot_profiles.periods(1).period_tags(10).create(refs=[])
        assert _post_json(mock_session) == {"snapshot_profile_period": 10, "refs": []}
        assert row.period_key == 10

    def test_create_requires_period(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="snapshot_profile_period is required"):
            mock_client.snapshot_profile_period_tags.create()

    def test_create_rejects_unknown_field(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="unknown snapshot_profile_period_tags field"):
            mock_client.snapshot_profile_period_tags.create(
                snapshot_profile_period=10, partial_tags="1"
            )

    def test_scoped_update_refuses_another_period(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 5,
            "snapshot_profile_period": 99,
        }
        with pytest.raises(NotFoundError, match="does not belong"):
            mock_client.snapshot_profiles.periods(1).period_tags(10).update(5, refs=[])
        methods = [call.kwargs.get("method") for call in mock_session.request.call_args_list]
        assert "PUT" not in methods

    def test_scoped_create_rejects_other_period(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="scoped to period 10"):
            mock_client.snapshot_profiles.periods(1).period_tags(10).create(
                snapshot_profile_period=11
            )

    def test_update_refs(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 6,
            "snapshot_profile_period": 10,
            "refs": [{"$key": 1}],
        }
        mock_client.snapshot_profile_period_tags.update(6, refs=[{"$key": 1}])
        assert _put_json(mock_session) == {"refs": [{"$key": 1}]}

    def test_update_without_fields_does_not_put(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 6,
            "snapshot_profile_period": 10,
        }
        mock_client.snapshot_profile_period_tags.update(6)
        methods = [call.kwargs.get("method") for call in mock_session.request.call_args_list]
        assert "PUT" not in methods

    def test_references_reads_refs_all(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 6,
            "snapshot_profile_period": 10,
            "refs": [{"$key": 4, "kept": "yes"}],
        }
        tag = SnapshotProfilePeriodTag(
            {"$key": 6, "snapshot_profile_period": 10, "refs": 0},
            mock_client.snapshot_profile_period_tags,
        )
        rows = tag.references()
        params = mock_session.request.call_args.kwargs["params"]
        assert params["fields"] == "refs[all]"
        assert rows[0].key == 4
        assert rows[0]["kept"] == "yes"

    def test_period_period_tags_is_scoped(self, mock_client: VergeClient) -> None:
        period = SnapshotProfilePeriod(
            {"$key": 10, "profile": 1},
            mock_client.snapshot_profiles.periods(1),
        )
        manager = period.period_tags()
        assert isinstance(manager, SnapshotProfilePeriodTagManager)
        assert manager._period_key == 10

    def test_delete_object(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""
        mock_session.request.return_value.json.return_value = {
            "$key": 6,
            "snapshot_profile_period": 10,
        }
        tag = SnapshotProfilePeriodTag(
            {"$key": 6, "snapshot_profile_period": 10},
            mock_client.snapshot_profile_period_tags,
        )
        tag.delete()
        methods = [call.kwargs.get("method") for call in mock_session.request.call_args_list]
        assert "DELETE" in methods
