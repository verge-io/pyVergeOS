"""Integration tests for Tag operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import contextlib
import random

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestTagCategoryListIntegration:
    """Integration tests for TagCategoryManager.list()."""

    def test_list_categories(self, live_client: VergeClient) -> None:
        """Test listing tag categories from live system."""
        categories = live_client.tag_categories.list()

        assert isinstance(categories, list)
        # May or may not have categories configured

    def test_list_categories_with_limit(self, live_client: VergeClient) -> None:
        """Test listing categories with limit."""
        categories = live_client.tag_categories.list(limit=1)

        assert isinstance(categories, list)
        assert len(categories) <= 1


@pytest.mark.integration
class TestTagCategoryGetIntegration:
    """Integration tests for TagCategoryManager.get()."""

    def test_get_category_by_key(self, live_client: VergeClient) -> None:
        """Test getting a category by key."""
        categories = live_client.tag_categories.list()
        if not categories:
            pytest.skip("No tag categories found on system")

        category = live_client.tag_categories.get(categories[0].key)

        assert category.key == categories[0].key
        assert category.name == categories[0].name

    def test_get_category_by_name(self, live_client: VergeClient) -> None:
        """Test getting a category by name."""
        categories = live_client.tag_categories.list()
        if not categories:
            pytest.skip("No tag categories found on system")

        category = live_client.tag_categories.get(name=categories[0].name)

        assert category.name == categories[0].name
        assert category.key == categories[0].key

    def test_get_nonexistent_category(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent category."""
        with pytest.raises(NotFoundError):
            live_client.tag_categories.get(999999)


@pytest.mark.integration
class TestTagCategoryPropertiesIntegration:
    """Integration tests for TagCategory property accessors."""

    def test_category_properties(self, live_client: VergeClient) -> None:
        """Test category property accessors on live data."""
        categories = live_client.tag_categories.list()
        if not categories:
            pytest.skip("No tag categories found on system")

        category = categories[0]

        # Test all properties are accessible
        _ = category.key
        _ = category.name
        _ = category.description
        _ = category.is_single_tag_selection
        _ = category.taggable_vms
        _ = category.taggable_networks
        _ = category.taggable_volumes
        _ = category.taggable_network_rules
        _ = category.taggable_vmware_containers
        _ = category.taggable_users
        _ = category.taggable_tenant_nodes
        _ = category.taggable_sites
        _ = category.taggable_nodes
        _ = category.taggable_groups
        _ = category.taggable_clusters
        _ = category.taggable_tenants
        _ = category.created
        _ = category.modified

    def test_category_taggable_types(self, live_client: VergeClient) -> None:
        """Test get_taggable_types method."""
        categories = live_client.tag_categories.list()
        if not categories:
            pytest.skip("No tag categories found on system")

        category = categories[0]
        types = category.get_taggable_types()

        assert isinstance(types, list)

    def test_category_tags_property(self, live_client: VergeClient) -> None:
        """Test tags property returns list."""
        categories = live_client.tag_categories.list()
        if not categories:
            pytest.skip("No tag categories found on system")

        category = categories[0]
        tags = category.tags

        assert isinstance(tags, list)


@pytest.mark.integration
class TestTagListIntegration:
    """Integration tests for TagManager.list()."""

    def test_list_tags(self, live_client: VergeClient) -> None:
        """Test listing tags from live system."""
        tags = live_client.tags.list()

        assert isinstance(tags, list)
        # May or may not have tags configured

    def test_list_tags_with_limit(self, live_client: VergeClient) -> None:
        """Test listing tags with limit."""
        tags = live_client.tags.list(limit=1)

        assert isinstance(tags, list)
        assert len(tags) <= 1

    def test_list_tags_by_category(self, live_client: VergeClient) -> None:
        """Test listing tags filtered by category."""
        categories = live_client.tag_categories.list()
        if not categories:
            pytest.skip("No tag categories found on system")

        tags = live_client.tags.list(category_key=categories[0].key)

        assert isinstance(tags, list)
        for tag in tags:
            assert tag.category_key == categories[0].key


@pytest.mark.integration
class TestTagGetIntegration:
    """Integration tests for TagManager.get()."""

    def test_get_tag_by_key(self, live_client: VergeClient) -> None:
        """Test getting a tag by key."""
        tags = live_client.tags.list()
        if not tags:
            pytest.skip("No tags found on system")

        tag = live_client.tags.get(tags[0].key)

        assert tag.key == tags[0].key
        assert tag.name == tags[0].name

    def test_get_tag_by_name(self, live_client: VergeClient) -> None:
        """Test getting a tag by name."""
        tags = live_client.tags.list()
        if not tags:
            pytest.skip("No tags found on system")

        tag = live_client.tags.get(name=tags[0].name, category_key=tags[0].category_key)

        assert tag.name == tags[0].name
        assert tag.key == tags[0].key

    def test_get_nonexistent_tag(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent tag."""
        with pytest.raises(NotFoundError):
            live_client.tags.get(999999)


@pytest.mark.integration
class TestTagPropertiesIntegration:
    """Integration tests for Tag property accessors."""

    def test_tag_properties(self, live_client: VergeClient) -> None:
        """Test tag property accessors on live data."""
        tags = live_client.tags.list()
        if not tags:
            pytest.skip("No tags found on system")

        tag = tags[0]

        # Test all properties are accessible
        _ = tag.key
        _ = tag.name
        _ = tag.description
        _ = tag.category_key
        _ = tag.category_name
        _ = tag.created
        _ = tag.modified


@pytest.mark.integration
class TestTagMemberListIntegration:
    """Integration tests for TagMemberManager.list()."""

    def test_list_members(self, live_client: VergeClient) -> None:
        """Test listing tag members from live system."""
        tags = live_client.tags.list()
        if not tags:
            pytest.skip("No tags found on system")

        members = live_client.tags.members(tags[0].key).list()

        assert isinstance(members, list)

    def test_list_members_via_tag_property(self, live_client: VergeClient) -> None:
        """Test listing members via tag.members property."""
        tags = live_client.tags.list()
        if not tags:
            pytest.skip("No tags found on system")

        tag = tags[0]
        members = tag.members.list()

        assert isinstance(members, list)


@pytest.mark.integration
class TestTagCRUDIntegration:
    """Integration tests for Tag CRUD operations."""

    @pytest.fixture
    def test_category(self, live_client: VergeClient):
        """Create a test category for tag tests."""
        category_name = f"pysdk-tag-test-{random.randint(10000, 99999)}"

        category = live_client.tag_categories.create(
            name=category_name,
            description="Test category for tag integration tests",
            taggable_vms=True,
            taggable_networks=True,
        )

        yield category

        # Cleanup
        with contextlib.suppress(Exception):
            # Delete any tags in the category first
            for tag in live_client.tags.list(category_key=category.key):
                with contextlib.suppress(Exception):
                    live_client.tags.delete(tag.key)
            live_client.tag_categories.delete(category.key)

    def test_create_and_delete_tag(
        self, live_client: VergeClient, test_category
    ) -> None:
        """Test creating and deleting a tag."""
        tag_name = f"pysdk-tag-{random.randint(10000, 99999)}"

        # Create tag
        tag = live_client.tags.create(
            name=tag_name,
            category_key=test_category.key,
            description="Integration test tag",
        )

        try:
            assert tag.name == tag_name
            assert tag.category_key == test_category.key
            assert tag.description == "Integration test tag"
            assert tag.key > 0

            # Verify we can get it
            fetched = live_client.tags.get(tag.key)
            assert fetched.name == tag_name
        finally:
            # Cleanup
            live_client.tags.delete(tag.key)

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.tags.get(tag.key)

    def test_update_tag(self, live_client: VergeClient, test_category) -> None:
        """Test updating a tag."""
        tag_name = f"pysdk-tag-{random.randint(10000, 99999)}"

        tag = live_client.tags.create(
            name=tag_name,
            category_key=test_category.key,
        )

        try:
            # Update description
            updated = live_client.tags.update(
                tag.key, description="Updated description"
            )
            assert updated.description == "Updated description"

            # Verify via refresh
            refreshed = tag.refresh()
            assert refreshed.description == "Updated description"
        finally:
            live_client.tags.delete(tag.key)

    def test_tag_refresh(self, live_client: VergeClient, test_category) -> None:
        """Test tag refresh method."""
        tag_name = f"pysdk-tag-{random.randint(10000, 99999)}"

        tag = live_client.tags.create(
            name=tag_name,
            category_key=test_category.key,
        )

        try:
            refreshed = tag.refresh()
            assert refreshed.key == tag.key
            assert refreshed.name == tag_name
        finally:
            live_client.tags.delete(tag.key)


@pytest.mark.integration
class TestTagCategoryCRUDIntegration:
    """Integration tests for TagCategory CRUD operations."""

    def test_create_and_delete_category(self, live_client: VergeClient) -> None:
        """Test creating and deleting a category."""
        category_name = f"pysdk-cat-{random.randint(10000, 99999)}"

        # Create category
        category = live_client.tag_categories.create(
            name=category_name,
            description="Integration test category",
            taggable_vms=True,
            taggable_networks=True,
            single_tag_selection=True,
        )

        try:
            assert category.name == category_name
            assert category.description == "Integration test category"
            assert category.taggable_vms is True
            assert category.taggable_networks is True
            assert category.is_single_tag_selection is True
            assert category.key > 0

            # Verify we can get it
            fetched = live_client.tag_categories.get(category.key)
            assert fetched.name == category_name
        finally:
            # Cleanup
            live_client.tag_categories.delete(category.key)

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.tag_categories.get(category.key)

    def test_update_category(self, live_client: VergeClient) -> None:
        """Test updating a category."""
        category_name = f"pysdk-cat-{random.randint(10000, 99999)}"

        category = live_client.tag_categories.create(
            name=category_name,
            taggable_vms=True,
        )

        try:
            # Update to enable more taggable types
            updated = live_client.tag_categories.update(
                category.key,
                description="Updated description",
                taggable_nodes=True,
            )
            assert updated.description == "Updated description"
            assert updated.taggable_nodes is True

            # Verify via refresh
            refreshed = category.refresh()
            assert refreshed.description == "Updated description"
        finally:
            live_client.tag_categories.delete(category.key)
