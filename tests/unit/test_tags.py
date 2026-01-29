"""Unit tests for tag, tag category, and tag member operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.tags import (
    RESOURCE_TYPE_DISPLAY,
    TAGGABLE_RESOURCE_TYPES,
    Tag,
    TagCategory,
    TagCategoryManager,
    TagManager,
    TagMember,
    TagMemberManager,
)


class TestTagMember:
    """Tests for TagMember resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 123}
        member = TagMember(data, MagicMock())
        assert member.key == 123

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        member = TagMember({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = member.key

    def test_tag_key_property(self) -> None:
        """Test tag_key property."""
        data = {"$key": 1, "tag": 5}
        member = TagMember(data, MagicMock())
        assert member.tag_key == 5

    def test_tag_key_default(self) -> None:
        """Test tag_key property defaults to 0."""
        member = TagMember({"$key": 1}, MagicMock())
        assert member.tag_key == 0

    def test_resource_ref_property(self) -> None:
        """Test resource_ref property."""
        data = {"$key": 1, "member": "vms/10"}
        member = TagMember(data, MagicMock())
        assert member.resource_ref == "vms/10"

    def test_resource_ref_empty(self) -> None:
        """Test resource_ref property when empty."""
        member = TagMember({"$key": 1}, MagicMock())
        assert member.resource_ref == ""

    def test_resource_type_vms(self) -> None:
        """Test resource_type property for VMs."""
        data = {"$key": 1, "member": "vms/10"}
        member = TagMember(data, MagicMock())
        assert member.resource_type == "vms"

    def test_resource_type_networks(self) -> None:
        """Test resource_type property for networks."""
        data = {"$key": 1, "member": "vnets/5"}
        member = TagMember(data, MagicMock())
        assert member.resource_type == "vnets"

    def test_resource_type_tenants(self) -> None:
        """Test resource_type property for tenants."""
        data = {"$key": 1, "member": "tenants/3"}
        member = TagMember(data, MagicMock())
        assert member.resource_type == "tenants"

    def test_resource_type_none(self) -> None:
        """Test resource_type property for empty ref."""
        member = TagMember({"$key": 1}, MagicMock())
        assert member.resource_type is None

    def test_resource_type_display(self) -> None:
        """Test resource_type_display property."""
        data = {"$key": 1, "member": "vms/10"}
        member = TagMember(data, MagicMock())
        assert member.resource_type_display == "Virtual Machine"

    def test_resource_type_display_network(self) -> None:
        """Test resource_type_display for networks."""
        data = {"$key": 1, "member": "vnets/5"}
        member = TagMember(data, MagicMock())
        assert member.resource_type_display == "Network"

    def test_resource_type_display_unknown(self) -> None:
        """Test resource_type_display for unknown type."""
        data = {"$key": 1, "member": "unknown/1"}
        member = TagMember(data, MagicMock())
        assert member.resource_type_display == "unknown"

    def test_resource_key_vm(self) -> None:
        """Test resource_key property for VMs."""
        data = {"$key": 1, "member": "vms/10"}
        member = TagMember(data, MagicMock())
        assert member.resource_key == 10

    def test_resource_key_network(self) -> None:
        """Test resource_key property for networks."""
        data = {"$key": 1, "member": "vnets/5"}
        member = TagMember(data, MagicMock())
        assert member.resource_key == 5

    def test_resource_key_invalid(self) -> None:
        """Test resource_key property for invalid ref."""
        data = {"$key": 1, "member": "vms/invalid"}
        member = TagMember(data, MagicMock())
        assert member.resource_key is None

    def test_resource_key_empty(self) -> None:
        """Test resource_key property for empty ref."""
        member = TagMember({"$key": 1}, MagicMock())
        assert member.resource_key is None

    def test_remove_method(self) -> None:
        """Test remove method calls manager."""
        mock_manager = MagicMock(spec=TagMemberManager)
        data = {"$key": 123}
        member = TagMember(data, mock_manager)

        member.remove()

        mock_manager.remove.assert_called_once_with(123)


class TestTag:
    """Tests for Tag resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 123}
        tag = Tag(data, MagicMock())
        assert tag.key == 123

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        tag = Tag({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = tag.key

    def test_name_property(self) -> None:
        """Test name property."""
        data = {"$key": 1, "name": "Production"}
        tag = Tag(data, MagicMock())
        assert tag.name == "Production"

    def test_description_property(self) -> None:
        """Test description property."""
        data = {"$key": 1, "description": "Production resources"}
        tag = Tag(data, MagicMock())
        assert tag.description == "Production resources"

    def test_description_none(self) -> None:
        """Test description property when not set."""
        tag = Tag({"$key": 1}, MagicMock())
        assert tag.description is None

    def test_category_key_property(self) -> None:
        """Test category_key property."""
        data = {"$key": 1, "category": 5}
        tag = Tag(data, MagicMock())
        assert tag.category_key == 5

    def test_category_key_default(self) -> None:
        """Test category_key property defaults to 0."""
        tag = Tag({"$key": 1}, MagicMock())
        assert tag.category_key == 0

    def test_category_name_property(self) -> None:
        """Test category_name property."""
        data = {"$key": 1, "category_name": "Environment"}
        tag = Tag(data, MagicMock())
        assert tag.category_name == "Environment"

    def test_category_name_none(self) -> None:
        """Test category_name property when not set."""
        tag = Tag({"$key": 1}, MagicMock())
        assert tag.category_name is None

    def test_created_property(self) -> None:
        """Test created property."""
        data = {"$key": 1, "created": 1706745600}
        tag = Tag(data, MagicMock())
        assert tag.created == 1706745600

    def test_created_none(self) -> None:
        """Test created property when not set."""
        tag = Tag({"$key": 1}, MagicMock())
        assert tag.created is None

    def test_modified_property(self) -> None:
        """Test modified property."""
        data = {"$key": 1, "modified": 1706745600}
        tag = Tag(data, MagicMock())
        assert tag.modified == 1706745600

    def test_modified_none(self) -> None:
        """Test modified property when not set."""
        tag = Tag({"$key": 1}, MagicMock())
        assert tag.modified is None

    def test_members_property(self) -> None:
        """Test members property returns manager."""
        mock_manager = MagicMock(spec=TagManager)
        mock_member_manager = MagicMock(spec=TagMemberManager)
        mock_manager.members.return_value = mock_member_manager

        data = {"$key": 123}
        tag = Tag(data, mock_manager)

        result = tag.members
        mock_manager.members.assert_called_once_with(123)
        assert result == mock_member_manager

    def test_refresh_method(self) -> None:
        """Test refresh method calls manager.get."""
        mock_manager = MagicMock(spec=TagManager)
        expected_tag = MagicMock(spec=Tag)
        mock_manager.get.return_value = expected_tag

        data = {"$key": 123}
        tag = Tag(data, mock_manager)

        result = tag.refresh()
        mock_manager.get.assert_called_once_with(123)
        assert result == expected_tag

    def test_save_method(self) -> None:
        """Test save method calls manager.update."""
        mock_manager = MagicMock(spec=TagManager)
        expected_tag = MagicMock(spec=Tag)
        mock_manager.update.return_value = expected_tag

        data = {"$key": 123}
        tag = Tag(data, mock_manager)

        result = tag.save(description="New description")
        mock_manager.update.assert_called_once_with(123, description="New description")
        assert result == expected_tag

    def test_delete_method(self) -> None:
        """Test delete method calls manager.delete."""
        mock_manager = MagicMock(spec=TagManager)
        data = {"$key": 123}
        tag = Tag(data, mock_manager)

        tag.delete()
        mock_manager.delete.assert_called_once_with(123)


class TestTagCategory:
    """Tests for TagCategory resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 123}
        category = TagCategory(data, MagicMock())
        assert category.key == 123

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        category = TagCategory({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = category.key

    def test_name_property(self) -> None:
        """Test name property."""
        data = {"$key": 1, "name": "Environment"}
        category = TagCategory(data, MagicMock())
        assert category.name == "Environment"

    def test_description_property(self) -> None:
        """Test description property."""
        data = {"$key": 1, "description": "Deployment environment"}
        category = TagCategory(data, MagicMock())
        assert category.description == "Deployment environment"

    def test_description_none(self) -> None:
        """Test description property when not set."""
        category = TagCategory({"$key": 1}, MagicMock())
        assert category.description is None

    def test_is_single_tag_selection_true(self) -> None:
        """Test is_single_tag_selection property when true."""
        data = {"$key": 1, "single_tag_selection": True}
        category = TagCategory(data, MagicMock())
        assert category.is_single_tag_selection is True

    def test_is_single_tag_selection_false(self) -> None:
        """Test is_single_tag_selection property when false."""
        data = {"$key": 1, "single_tag_selection": False}
        category = TagCategory(data, MagicMock())
        assert category.is_single_tag_selection is False

    def test_is_single_tag_selection_default(self) -> None:
        """Test is_single_tag_selection property default."""
        category = TagCategory({"$key": 1}, MagicMock())
        assert category.is_single_tag_selection is False

    def test_taggable_vms_property(self) -> None:
        """Test taggable_vms property."""
        data = {"$key": 1, "taggable_vms": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_vms is True

    def test_taggable_vms_default(self) -> None:
        """Test taggable_vms property default."""
        category = TagCategory({"$key": 1}, MagicMock())
        assert category.taggable_vms is False

    def test_taggable_networks_property(self) -> None:
        """Test taggable_networks property."""
        data = {"$key": 1, "taggable_vnets": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_networks is True

    def test_taggable_volumes_property(self) -> None:
        """Test taggable_volumes property."""
        data = {"$key": 1, "taggable_volumes": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_volumes is True

    def test_taggable_network_rules_property(self) -> None:
        """Test taggable_network_rules property."""
        data = {"$key": 1, "taggable_vnet_rules": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_network_rules is True

    def test_taggable_vmware_containers_property(self) -> None:
        """Test taggable_vmware_containers property."""
        data = {"$key": 1, "taggable_vmware_containers": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_vmware_containers is True

    def test_taggable_users_property(self) -> None:
        """Test taggable_users property."""
        data = {"$key": 1, "taggable_users": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_users is True

    def test_taggable_tenant_nodes_property(self) -> None:
        """Test taggable_tenant_nodes property."""
        data = {"$key": 1, "taggable_tenant_nodes": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_tenant_nodes is True

    def test_taggable_sites_property(self) -> None:
        """Test taggable_sites property."""
        data = {"$key": 1, "taggable_sites": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_sites is True

    def test_taggable_nodes_property(self) -> None:
        """Test taggable_nodes property."""
        data = {"$key": 1, "taggable_nodes": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_nodes is True

    def test_taggable_groups_property(self) -> None:
        """Test taggable_groups property."""
        data = {"$key": 1, "taggable_groups": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_groups is True

    def test_taggable_clusters_property(self) -> None:
        """Test taggable_clusters property."""
        data = {"$key": 1, "taggable_clusters": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_clusters is True

    def test_taggable_tenants_property(self) -> None:
        """Test taggable_tenants property."""
        data = {"$key": 1, "taggable_tenants": True}
        category = TagCategory(data, MagicMock())
        assert category.taggable_tenants is True

    def test_created_property(self) -> None:
        """Test created property."""
        data = {"$key": 1, "created": 1706745600}
        category = TagCategory(data, MagicMock())
        assert category.created == 1706745600

    def test_modified_property(self) -> None:
        """Test modified property."""
        data = {"$key": 1, "modified": 1706745600}
        category = TagCategory(data, MagicMock())
        assert category.modified == 1706745600

    def test_get_taggable_types_empty(self) -> None:
        """Test get_taggable_types with no types enabled."""
        category = TagCategory({"$key": 1}, MagicMock())
        assert category.get_taggable_types() == []

    def test_get_taggable_types_vms(self) -> None:
        """Test get_taggable_types with VMs enabled."""
        data = {"$key": 1, "taggable_vms": True}
        category = TagCategory(data, MagicMock())
        assert "vms" in category.get_taggable_types()

    def test_get_taggable_types_multiple(self) -> None:
        """Test get_taggable_types with multiple types enabled."""
        data = {
            "$key": 1,
            "taggable_vms": True,
            "taggable_vnets": True,
            "taggable_tenants": True,
        }
        category = TagCategory(data, MagicMock())
        types = category.get_taggable_types()
        assert "vms" in types
        assert "vnets" in types
        assert "tenants" in types

    def test_tags_property(self) -> None:
        """Test tags property returns list of tags."""
        mock_manager = MagicMock(spec=TagCategoryManager)
        mock_client = MagicMock()
        mock_tags = [MagicMock(spec=Tag), MagicMock(spec=Tag)]
        mock_client.tags.list.return_value = mock_tags
        mock_manager._client = mock_client

        data = {"$key": 123}
        category = TagCategory(data, mock_manager)

        result = category.tags
        mock_client.tags.list.assert_called_once_with(category_key=123)
        assert result == mock_tags

    def test_refresh_method(self) -> None:
        """Test refresh method calls manager.get."""
        mock_manager = MagicMock(spec=TagCategoryManager)
        expected_category = MagicMock(spec=TagCategory)
        mock_manager.get.return_value = expected_category

        data = {"$key": 123}
        category = TagCategory(data, mock_manager)

        result = category.refresh()
        mock_manager.get.assert_called_once_with(123)
        assert result == expected_category

    def test_save_method(self) -> None:
        """Test save method calls manager.update."""
        mock_manager = MagicMock(spec=TagCategoryManager)
        expected_category = MagicMock(spec=TagCategory)
        mock_manager.update.return_value = expected_category

        data = {"$key": 123}
        category = TagCategory(data, mock_manager)

        result = category.save(description="New description")
        mock_manager.update.assert_called_once_with(123, description="New description")
        assert result == expected_category

    def test_delete_method(self) -> None:
        """Test delete method calls manager.delete."""
        mock_manager = MagicMock(spec=TagCategoryManager)
        data = {"$key": 123}
        category = TagCategory(data, mock_manager)

        category.delete()
        mock_manager.delete.assert_called_once_with(123)


class TestTagMemberManager:
    """Tests for TagMemberManager."""

    def test_init(self) -> None:
        """Test TagMemberManager initialization."""
        mock_client = MagicMock()
        manager = TagMemberManager(mock_client, tag_key=123)
        assert manager._tag_key == 123
        assert manager._endpoint == "tag_members"

    def test_list_empty(self) -> None:
        """Test list returns empty list when no members."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.list()
        assert result == []
        mock_client._request.assert_called_once()

    def test_list_with_members(self) -> None:
        """Test list returns TagMember objects."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 1, "tag": 123, "member": "vms/10"},
            {"$key": 2, "tag": 123, "member": "vnets/5"},
        ]
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.list()
        assert len(result) == 2
        assert all(isinstance(m, TagMember) for m in result)
        assert result[0].resource_ref == "vms/10"
        assert result[1].resource_ref == "vnets/5"

    def test_list_filter_by_tag(self) -> None:
        """Test list includes tag filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = TagMemberManager(mock_client, tag_key=123)

        manager.list()

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "tag eq 123" in params["filter"]

    def test_list_filter_by_resource_type(self) -> None:
        """Test list filters by resource type."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 1, "tag": 123, "member": "vms/10"},
            {"$key": 2, "tag": 123, "member": "vnets/5"},
        ]
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.list(resource_type="vms")
        assert len(result) == 1
        assert result[0].resource_type == "vms"

    def test_add(self) -> None:
        """Test add method creates member."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 999}
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.add("vms", 10)

        assert result.key == 999
        assert result.tag_key == 123
        assert result.resource_ref == "vms/10"

        call_args = mock_client._request.call_args
        assert call_args[1]["json_data"]["tag"] == 123
        assert call_args[1]["json_data"]["member"] == "vms/10"

    def test_add_vm(self) -> None:
        """Test add_vm convenience method."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 999}
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.add_vm(10)

        assert result.resource_ref == "vms/10"

    def test_add_network(self) -> None:
        """Test add_network convenience method."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 999}
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.add_network(5)

        assert result.resource_ref == "vnets/5"

    def test_add_tenant(self) -> None:
        """Test add_tenant convenience method."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 999}
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.add_tenant(3)

        assert result.resource_ref == "tenants/3"

    def test_add_user(self) -> None:
        """Test add_user convenience method."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 999}
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.add_user(7)

        assert result.resource_ref == "users/7"

    def test_add_node(self) -> None:
        """Test add_node convenience method."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 999}
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.add_node(2)

        assert result.resource_ref == "nodes/2"

    def test_add_cluster(self) -> None:
        """Test add_cluster convenience method."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 999}
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.add_cluster(1)

        assert result.resource_ref == "clusters/1"

    def test_add_site(self) -> None:
        """Test add_site convenience method."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 999}
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.add_site(4)

        assert result.resource_ref == "sites/4"

    def test_add_group(self) -> None:
        """Test add_group convenience method."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 999}
        manager = TagMemberManager(mock_client, tag_key=123)

        result = manager.add_group(6)

        assert result.resource_ref == "groups/6"

    def test_remove(self) -> None:
        """Test remove method."""
        mock_client = MagicMock()
        manager = TagMemberManager(mock_client, tag_key=123)

        manager.remove(999)

        mock_client._request.assert_called_once_with("DELETE", "tag_members/999")

    def test_remove_resource(self) -> None:
        """Test remove_resource method."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            [{"$key": 999, "tag": 123, "member": "vms/10"}],  # list call
            None,  # delete call
        ]
        manager = TagMemberManager(mock_client, tag_key=123)

        manager.remove_resource("vms", 10)

        assert mock_client._request.call_count == 2

    def test_remove_resource_not_found(self) -> None:
        """Test remove_resource raises when not found."""
        mock_client = MagicMock()
        mock_client._request.return_value = []  # empty list
        manager = TagMemberManager(mock_client, tag_key=123)

        with pytest.raises(NotFoundError, match="not tagged"):
            manager.remove_resource("vms", 999)

    def test_remove_vm(self) -> None:
        """Test remove_vm convenience method."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            [{"$key": 999, "tag": 123, "member": "vms/10"}],
            None,
        ]
        manager = TagMemberManager(mock_client, tag_key=123)

        manager.remove_vm(10)

        assert mock_client._request.call_count == 2

    def test_remove_network(self) -> None:
        """Test remove_network convenience method."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            [{"$key": 999, "tag": 123, "member": "vnets/5"}],
            None,
        ]
        manager = TagMemberManager(mock_client, tag_key=123)

        manager.remove_network(5)

        assert mock_client._request.call_count == 2

    def test_remove_tenant(self) -> None:
        """Test remove_tenant convenience method."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            [{"$key": 999, "tag": 123, "member": "tenants/3"}],
            None,
        ]
        manager = TagMemberManager(mock_client, tag_key=123)

        manager.remove_tenant(3)

        assert mock_client._request.call_count == 2


class TestTagManager:
    """Tests for TagManager."""

    def test_init(self) -> None:
        """Test TagManager initialization."""
        mock_client = MagicMock()
        manager = TagManager(mock_client)
        assert manager._endpoint == "tags"

    def test_list_empty(self) -> None:
        """Test list returns empty list when no tags."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = TagManager(mock_client)

        result = manager.list()
        assert result == []

    def test_list_with_tags(self) -> None:
        """Test list returns Tag objects."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 1, "name": "Production", "category": 1},
            {"$key": 2, "name": "Development", "category": 1},
        ]
        manager = TagManager(mock_client)

        result = manager.list()
        assert len(result) == 2
        assert all(isinstance(t, Tag) for t in result)
        assert result[0].name == "Production"
        assert result[1].name == "Development"

    def test_list_filter_by_category_key(self) -> None:
        """Test list filters by category key."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = TagManager(mock_client)

        manager.list(category_key=5)

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "category eq 5" in params["filter"]

    def test_list_filter_by_category_name(self) -> None:
        """Test list filters by category name (with lookup)."""
        mock_client = MagicMock()
        # First call returns category lookup, second returns tags
        mock_client._request.side_effect = [
            [{"$key": 5, "name": "Environment"}],  # category lookup
            [],  # tag list
        ]
        manager = TagManager(mock_client)

        manager.list(category_name="Environment")

        # Should have made two calls
        assert mock_client._request.call_count == 2

    def test_list_filter_by_name(self) -> None:
        """Test list filters by name."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = TagManager(mock_client)

        manager.list(name="Production")

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "name eq 'Production'" in params["filter"]

    def test_get_by_key(self) -> None:
        """Test get by key returns Tag object."""
        mock_client = MagicMock()
        mock_client._request.return_value = {
            "$key": 123,
            "name": "Production",
            "category": 1,
        }
        manager = TagManager(mock_client)

        result = manager.get(123)

        assert isinstance(result, Tag)
        assert result.key == 123
        assert result.name == "Production"
        mock_client._request.assert_called_once()

    def test_get_by_key_not_found(self) -> None:
        """Test get by key raises NotFoundError."""
        mock_client = MagicMock()
        mock_client._request.return_value = None
        manager = TagManager(mock_client)

        with pytest.raises(NotFoundError, match="key 123 not found"):
            manager.get(123)

    def test_get_by_name(self) -> None:
        """Test get by name returns Tag object."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 123, "name": "Production", "category": 1}
        ]
        manager = TagManager(mock_client)

        result = manager.get(name="Production")

        assert isinstance(result, Tag)
        assert result.name == "Production"

    def test_get_by_name_not_found(self) -> None:
        """Test get by name raises NotFoundError."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = TagManager(mock_client)

        with pytest.raises(NotFoundError, match="'Production' not found"):
            manager.get(name="Production")

    def test_get_no_args(self) -> None:
        """Test get raises ValueError when no args provided."""
        mock_client = MagicMock()
        manager = TagManager(mock_client)

        with pytest.raises(ValueError, match="Either key or name must be provided"):
            manager.get()

    def test_create(self) -> None:
        """Test create method."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            {"$key": 123},  # POST create
            {"$key": 123, "name": "Production", "category": 1},  # GET after create
        ]
        manager = TagManager(mock_client)

        result = manager.create(name="Production", category_key=1)

        assert isinstance(result, Tag)
        assert result.name == "Production"

    def test_create_with_description(self) -> None:
        """Test create method with description."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            {"$key": 123},
            {"$key": 123, "name": "Production", "description": "Prod resources"},
        ]
        manager = TagManager(mock_client)

        manager.create(
            name="Production",
            category_key=1,
            description="Prod resources",
        )

        # Check the POST call included description
        call_args = mock_client._request.call_args_list[0]
        assert call_args[1]["json_data"]["description"] == "Prod resources"

    def test_update(self) -> None:
        """Test update method."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            None,  # PUT update
            {"$key": 123, "name": "Production", "description": "Updated"},  # GET
        ]
        manager = TagManager(mock_client)

        result = manager.update(123, description="Updated")

        assert isinstance(result, Tag)
        mock_client._request.assert_any_call("PUT", "tags/123", json_data={"description": "Updated"})

    def test_update_no_changes(self) -> None:
        """Test update with no changes returns current tag."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 123, "name": "Production"}
        manager = TagManager(mock_client)

        manager.update(123)

        # Should just do GET, not PUT
        mock_client._request.assert_called_once()
        assert "GET" in str(mock_client._request.call_args)

    def test_delete(self) -> None:
        """Test delete method."""
        mock_client = MagicMock()
        manager = TagManager(mock_client)

        manager.delete(123)

        mock_client._request.assert_called_once_with("DELETE", "tags/123")

    def test_members(self) -> None:
        """Test members method returns TagMemberManager."""
        mock_client = MagicMock()
        manager = TagManager(mock_client)

        result = manager.members(123)

        assert isinstance(result, TagMemberManager)
        assert result._tag_key == 123


class TestTagCategoryManager:
    """Tests for TagCategoryManager."""

    def test_init(self) -> None:
        """Test TagCategoryManager initialization."""
        mock_client = MagicMock()
        manager = TagCategoryManager(mock_client)
        assert manager._endpoint == "tag_categories"

    def test_list_empty(self) -> None:
        """Test list returns empty list when no categories."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = TagCategoryManager(mock_client)

        result = manager.list()
        assert result == []

    def test_list_with_categories(self) -> None:
        """Test list returns TagCategory objects."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 1, "name": "Environment", "taggable_vms": True},
            {"$key": 2, "name": "CostCenter", "taggable_vms": True},
        ]
        manager = TagCategoryManager(mock_client)

        result = manager.list()
        assert len(result) == 2
        assert all(isinstance(c, TagCategory) for c in result)
        assert result[0].name == "Environment"
        assert result[1].name == "CostCenter"

    def test_get_by_key(self) -> None:
        """Test get by key returns TagCategory object."""
        mock_client = MagicMock()
        mock_client._request.return_value = {
            "$key": 123,
            "name": "Environment",
            "taggable_vms": True,
        }
        manager = TagCategoryManager(mock_client)

        result = manager.get(123)

        assert isinstance(result, TagCategory)
        assert result.key == 123
        assert result.name == "Environment"

    def test_get_by_key_not_found(self) -> None:
        """Test get by key raises NotFoundError."""
        mock_client = MagicMock()
        mock_client._request.return_value = None
        manager = TagCategoryManager(mock_client)

        with pytest.raises(NotFoundError, match="key 123 not found"):
            manager.get(123)

    def test_get_by_name(self) -> None:
        """Test get by name returns TagCategory object."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 123, "name": "Environment", "taggable_vms": True}
        ]
        manager = TagCategoryManager(mock_client)

        result = manager.get(name="Environment")

        assert isinstance(result, TagCategory)
        assert result.name == "Environment"

    def test_get_by_name_not_found(self) -> None:
        """Test get by name raises NotFoundError."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = TagCategoryManager(mock_client)

        with pytest.raises(NotFoundError, match="'Environment' not found"):
            manager.get(name="Environment")

    def test_get_no_args(self) -> None:
        """Test get raises ValueError when no args provided."""
        mock_client = MagicMock()
        manager = TagCategoryManager(mock_client)

        with pytest.raises(ValueError, match="Either key or name must be provided"):
            manager.get()

    def test_create_basic(self) -> None:
        """Test create method with minimum args."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            {"$key": 123},  # POST create
            {"$key": 123, "name": "Environment"},  # GET after create
        ]
        manager = TagCategoryManager(mock_client)

        result = manager.create(name="Environment")

        assert isinstance(result, TagCategory)
        assert result.name == "Environment"

    def test_create_with_all_options(self) -> None:
        """Test create method with all options."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            {"$key": 123},
            {"$key": 123, "name": "Environment", "taggable_vms": True},
        ]
        manager = TagCategoryManager(mock_client)

        manager.create(
            name="Environment",
            description="Deployment environment",
            single_tag_selection=True,
            taggable_vms=True,
            taggable_networks=True,
            taggable_tenants=True,
        )

        # Check the POST call
        call_args = mock_client._request.call_args_list[0]
        body = call_args[1]["json_data"]
        assert body["name"] == "Environment"
        assert body["description"] == "Deployment environment"
        assert body["single_tag_selection"] is True
        assert body["taggable_vms"] is True
        assert body["taggable_vnets"] is True
        assert body["taggable_tenants"] is True

    def test_create_all_taggable_types(self) -> None:
        """Test create with all taggable types."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [{"$key": 123}, {"$key": 123, "name": "All"}]
        manager = TagCategoryManager(mock_client)

        manager.create(
            name="All",
            taggable_vms=True,
            taggable_networks=True,
            taggable_volumes=True,
            taggable_network_rules=True,
            taggable_vmware_containers=True,
            taggable_users=True,
            taggable_tenant_nodes=True,
            taggable_sites=True,
            taggable_nodes=True,
            taggable_groups=True,
            taggable_clusters=True,
            taggable_tenants=True,
        )

        call_args = mock_client._request.call_args_list[0]
        body = call_args[1]["json_data"]
        assert body["taggable_vms"] is True
        assert body["taggable_vnets"] is True
        assert body["taggable_volumes"] is True
        assert body["taggable_vnet_rules"] is True
        assert body["taggable_vmware_containers"] is True
        assert body["taggable_users"] is True
        assert body["taggable_tenant_nodes"] is True
        assert body["taggable_sites"] is True
        assert body["taggable_nodes"] is True
        assert body["taggable_groups"] is True
        assert body["taggable_clusters"] is True
        assert body["taggable_tenants"] is True

    def test_update(self) -> None:
        """Test update method."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            None,  # PUT update
            {"$key": 123, "name": "Environment", "description": "Updated"},  # GET
        ]
        manager = TagCategoryManager(mock_client)

        result = manager.update(123, description="Updated")

        assert isinstance(result, TagCategory)
        mock_client._request.assert_any_call(
            "PUT", "tag_categories/123", json_data={"description": "Updated"}
        )

    def test_update_taggable_types(self) -> None:
        """Test update can modify taggable types."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            None,
            {"$key": 123, "name": "Environment", "taggable_nodes": True},
        ]
        manager = TagCategoryManager(mock_client)

        manager.update(123, taggable_nodes=True, taggable_clusters=True)

        call_args = mock_client._request.call_args_list[0]
        body = call_args[1]["json_data"]
        assert body["taggable_nodes"] is True
        assert body["taggable_clusters"] is True

    def test_update_no_changes(self) -> None:
        """Test update with no changes returns current category."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 123, "name": "Environment"}
        manager = TagCategoryManager(mock_client)

        manager.update(123)

        # Should just do GET, not PUT
        mock_client._request.assert_called_once()

    def test_delete(self) -> None:
        """Test delete method."""
        mock_client = MagicMock()
        manager = TagCategoryManager(mock_client)

        manager.delete(123)

        mock_client._request.assert_called_once_with("DELETE", "tag_categories/123")


class TestConstants:
    """Tests for module constants."""

    def test_taggable_resource_types(self) -> None:
        """Test TAGGABLE_RESOURCE_TYPES mapping."""
        assert TAGGABLE_RESOURCE_TYPES["vms"] == "taggable_vms"
        assert TAGGABLE_RESOURCE_TYPES["vnets"] == "taggable_vnets"
        assert TAGGABLE_RESOURCE_TYPES["tenants"] == "taggable_tenants"
        assert TAGGABLE_RESOURCE_TYPES["nodes"] == "taggable_nodes"
        assert TAGGABLE_RESOURCE_TYPES["clusters"] == "taggable_clusters"

    def test_resource_type_display(self) -> None:
        """Test RESOURCE_TYPE_DISPLAY mapping."""
        assert RESOURCE_TYPE_DISPLAY["vms"] == "Virtual Machine"
        assert RESOURCE_TYPE_DISPLAY["vnets"] == "Network"
        assert RESOURCE_TYPE_DISPLAY["tenants"] == "Tenant"
        assert RESOURCE_TYPE_DISPLAY["nodes"] == "Node"
        assert RESOURCE_TYPE_DISPLAY["clusters"] == "Cluster"
