"""Integration tests for tag-scoped snapshot profile periods.

These tests require a live VergeOS system and are skipped when
VERGE_HOST, VERGE_USERNAME and VERGE_PASSWORD are not set.
"""

from __future__ import annotations

import uuid

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.integration
class TestPeriodTagTableIntegration:
    """The two tables answer list() on a live server."""

    def test_list_period_tags(self, live_client: VergeClient) -> None:
        rows = live_client.snapshot_profile_period_tags.list(limit=5)
        assert isinstance(rows, list)
        for row in rows:
            assert row.key
            assert row.period_key is not None

    def test_list_tag_references(self, live_client: VergeClient) -> None:
        rows = live_client.tag_references.list(limit=5)
        assert isinstance(rows, list)
        widened = live_client.tag_references.list(limit=5, fields="all")
        assert isinstance(widened, list)


@pytest.mark.integration
class TestPeriodTagScopeIntegration:
    """Write tag scope onto a period and read it back."""

    def test_include_and_clear(self, live_client: VergeClient) -> None:
        category_name = unique_name("pyvergeos-period-tag")
        tag_name = unique_name("pyvergeos-db")
        profile_name = unique_name("pyvergeos-profile")
        category = live_client.tag_categories.create(
            name=category_name,
            description="Period tag integration test",
            taggable_vms=True,
        )
        tag = None
        profile = None
        try:
            tag = live_client.tags.create(name=tag_name, category_key=category.key)
            profile = live_client.snapshot_profiles.create(name=profile_name)
            period = profile.add_period(
                name="Hourly",
                frequency="hourly",
                retention_seconds=3600,
                include_tags=[tag_name],
                quiesce_tags=[tag.key],
            )
            assert period.snapshot_type == "partial_include"
            assert period.partial_tag_keys == [tag.key]
            assert period.quiesce_tag_keys == [tag.key]

            fetched = live_client.snapshot_profiles.periods(profile.key).get(period.key)
            assert fetched.snapshot_type == "partial_include"
            assert fetched.partial_tag_keys == [tag.key]
            assert fetched.quiesce_tag_keys == [tag.key]

            joined = period.period_tags().list()
            assert isinstance(joined, list)
            for row in joined:
                assert row.period_key == period.key
                children = row.references()
                assert isinstance(children, list)

            cleared = live_client.snapshot_profiles.periods(profile.key).update(
                period.key,
                snapshot_type="full",
            )
            assert cleared.snapshot_type == "full"
            assert cleared.partial_tag_keys == []
            assert cleared.quiesce_tag_keys == []
        finally:
            if profile is not None:
                for period in live_client.snapshot_profiles.periods(profile.key).list():
                    period.delete()
                live_client.snapshot_profiles.delete(profile.key)
            if tag is not None:
                live_client.tags.delete(tag.key)
            live_client.tag_categories.delete(category.key)

    def test_exclude_tags(self, live_client: VergeClient) -> None:
        category = live_client.tag_categories.create(
            name=unique_name("pyvergeos-period-ex"),
            taggable_vms=True,
        )
        profile = None
        try:
            tag = live_client.tags.create(
                name=unique_name("pyvergeos-skip"),
                category_key=category.key,
            )
            profile = live_client.snapshot_profiles.create(name=unique_name("pyvergeos-ex"))
            period = live_client.snapshot_profiles.periods(profile.key).create(
                name="Daily",
                frequency="daily",
                retention=86400,
                exclude_tags=[tag.key],
            )
            assert period.snapshot_type == "partial_exclude"
            assert period.partial_tag_keys == [tag.key]
            assert period.quiesce_tag_keys == []
        finally:
            if profile is not None:
                for period in live_client.snapshot_profiles.periods(profile.key).list():
                    period.delete()
                live_client.snapshot_profiles.delete(profile.key)
            live_client.tag_categories.delete(category.key)

    def test_include_and_exclude_create_nothing(self, live_client: VergeClient) -> None:
        profile = live_client.snapshot_profiles.create(name=unique_name("pyvergeos-bad"))
        try:
            with pytest.raises(ValueError, match="mutually exclusive"):
                live_client.snapshot_profiles.periods(profile.key).create(
                    name="Nope",
                    frequency="daily",
                    retention=86400,
                    include_tags=[1],
                    exclude_tags=[2],
                )
            assert live_client.snapshot_profiles.periods(profile.key).list() == []
        finally:
            live_client.snapshot_profiles.delete(profile.key)

    def test_missing_period_tag(self, live_client: VergeClient) -> None:
        with pytest.raises(NotFoundError):
            live_client.snapshot_profile_period_tags.get(999999999)
