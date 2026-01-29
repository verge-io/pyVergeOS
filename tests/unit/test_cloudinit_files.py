"""Unit tests for CloudInitFile operations."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.cloudinit_files import (
    RENDER_TYPE_DISPLAY,
    RENDER_TYPE_MAP,
    CloudInitFile,
)

# =============================================================================
# CloudInitFile Model Tests
# =============================================================================


class TestCloudInitFile:
    """Unit tests for CloudInitFile model."""

    def test_cloudinit_file_properties(self, mock_client: VergeClient) -> None:
        """Test CloudInitFile property accessors."""
        now_ts = int(time.time())
        data = {
            "$key": 1,
            "name": "/user-data",
            "owner": "vms/123",
            "filesize": 256,
            "allocated_bytes": 512,
            "used_bytes": 256,
            "modified": now_ts,
            "render": "jinja2",
            "contains_variables": False,
            "creator": "admin",
        }
        file = CloudInitFile(data, mock_client.cloudinit_files)

        assert file.key == 1
        assert file.name == "/user-data"
        assert file.owner == "vms/123"
        assert file.vm_key == 123
        assert file.filesize == 256
        assert file.allocated_bytes == 512
        assert file.used_bytes == 256
        assert file.render == "jinja2"
        assert file.render_display == "Jinja2"
        assert file.contains_variables is False
        assert file.creator == "admin"
        assert file.modified_at is not None

    def test_cloudinit_file_default_values(self, mock_client: VergeClient) -> None:
        """Test CloudInitFile default values for missing fields."""
        data = {"$key": 1}
        file = CloudInitFile(data, mock_client.cloudinit_files)

        assert file.name == ""
        assert file.owner == ""
        assert file.vm_key is None
        assert file.filesize == 0
        assert file.allocated_bytes == 0
        assert file.used_bytes == 0
        assert file.render == "no"
        assert file.render_display == "No"
        assert file.contains_variables is False
        assert file.creator == ""
        assert file.modified_at is None
        assert file.contents is None

    def test_cloudinit_file_render_display_no(self, mock_client: VergeClient) -> None:
        """Test render_display for 'no' render type."""
        data = {"$key": 1, "render": "no"}
        file = CloudInitFile(data, mock_client.cloudinit_files)
        assert file.render_display == "No"

    def test_cloudinit_file_render_display_variables(self, mock_client: VergeClient) -> None:
        """Test render_display for 'variables' render type."""
        data = {"$key": 1, "render": "variables"}
        file = CloudInitFile(data, mock_client.cloudinit_files)
        assert file.render_display == "Variables"

    def test_cloudinit_file_render_display_jinja2(self, mock_client: VergeClient) -> None:
        """Test render_display for 'jinja2' render type."""
        data = {"$key": 1, "render": "jinja2"}
        file = CloudInitFile(data, mock_client.cloudinit_files)
        assert file.render_display == "Jinja2"

    def test_cloudinit_file_vm_key_parsing(self, mock_client: VergeClient) -> None:
        """Test vm_key parsing from owner."""
        data = {"$key": 1, "owner": "vms/456"}
        file = CloudInitFile(data, mock_client.cloudinit_files)
        assert file.vm_key == 456

    def test_cloudinit_file_vm_key_invalid_owner(self, mock_client: VergeClient) -> None:
        """Test vm_key returns None for invalid owner format."""
        data = {"$key": 1, "owner": "tenants/123"}
        file = CloudInitFile(data, mock_client.cloudinit_files)
        assert file.vm_key is None

    def test_cloudinit_file_vm_key_empty_owner(self, mock_client: VergeClient) -> None:
        """Test vm_key returns None for empty owner."""
        data = {"$key": 1, "owner": ""}
        file = CloudInitFile(data, mock_client.cloudinit_files)
        assert file.vm_key is None

    def test_cloudinit_file_modified_at_none(self, mock_client: VergeClient) -> None:
        """Test modified_at returns None when modified is 0."""
        data = {"$key": 1, "modified": 0}
        file = CloudInitFile(data, mock_client.cloudinit_files)
        assert file.modified_at is None

    def test_cloudinit_file_modified_at_valid(self, mock_client: VergeClient) -> None:
        """Test modified_at returns correct datetime."""
        now_ts = int(time.time())
        data = {"$key": 1, "modified": now_ts}
        file = CloudInitFile(data, mock_client.cloudinit_files)
        assert file.modified_at is not None
        assert isinstance(file.modified_at, datetime)
        assert file.modified_at.tzinfo == timezone.utc

    def test_cloudinit_file_contents_property(self, mock_client: VergeClient) -> None:
        """Test contents property returns value when set."""
        data = {"$key": 1, "contents": "#cloud-config\ntest: true"}
        file = CloudInitFile(data, mock_client.cloudinit_files)
        assert file.contents == "#cloud-config\ntest: true"

    def test_cloudinit_file_contents_none(self, mock_client: VergeClient) -> None:
        """Test contents property returns None when not set."""
        data = {"$key": 1}
        file = CloudInitFile(data, mock_client.cloudinit_files)
        assert file.contents is None

    def test_cloudinit_file_repr(self, mock_client: VergeClient) -> None:
        """Test CloudInitFile string representation."""
        data = {"$key": 1, "name": "/user-data", "owner": "vms/123"}
        file = CloudInitFile(data, mock_client.cloudinit_files)

        repr_str = repr(file)
        assert "CloudInitFile" in repr_str
        assert "key=1" in repr_str
        assert "/user-data" in repr_str
        assert "vm_key=123" in repr_str


# =============================================================================
# CloudInitFileManager Tests
# =============================================================================


class TestCloudInitFileManager:
    """Unit tests for CloudInitFileManager."""

    def test_manager_endpoint(self, mock_client: VergeClient) -> None:
        """Test manager has correct endpoint."""
        assert mock_client.cloudinit_files._endpoint == "cloudinit_files"

    def test_list_cloudinit_files(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing cloud-init files."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},
            {"$key": 2, "name": "/meta-data", "owner": "vms/100"},
        ]

        files = mock_client.cloudinit_files.list()

        assert len(files) == 2
        assert files[0].name == "/user-data"
        assert files[1].name == "/meta-data"

    def test_list_cloudinit_files_empty(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing cloud-init files returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        files = mock_client.cloudinit_files.list()
        assert files == []

    def test_list_cloudinit_files_with_vm_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing cloud-init files with VM key filter."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "/user-data", "owner": "vms/100"}
        ]

        files = mock_client.cloudinit_files.list(vm_key=100)

        assert len(files) == 1
        # Verify filter was applied
        call_args = mock_session.request.call_args
        assert "owner eq 'vms/100'" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_cloudinit_files_with_name_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing cloud-init files with name filter."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "/user-data", "owner": "vms/100"}
        ]

        files = mock_client.cloudinit_files.list(name="/user-data")

        assert len(files) == 1
        call_args = mock_session.request.call_args
        assert "name eq '/user-data'" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_cloudinit_files_with_wildcard_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing cloud-init files with wildcard name filter."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},
            {"$key": 2, "name": "/user-data-2", "owner": "vms/100"},
        ]

        files = mock_client.cloudinit_files.list(name="*user*")

        assert len(files) == 2
        call_args = mock_session.request.call_args
        assert "name ct 'user'" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_cloudinit_files_with_render_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing cloud-init files with render type filter."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "/user-data", "render": "jinja2"}
        ]

        files = mock_client.cloudinit_files.list(render="Jinja2")

        assert len(files) == 1
        call_args = mock_session.request.call_args
        assert "render eq 'jinja2'" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_get_cloudinit_file_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting cloud-init file by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "/user-data",
            "owner": "vms/100",
        }

        file = mock_client.cloudinit_files.get(1)

        assert file.key == 1
        assert file.name == "/user-data"

    def test_get_cloudinit_file_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting cloud-init file by name and vm_key."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "/user-data", "owner": "vms/100"}
        ]

        file = mock_client.cloudinit_files.get(name="/user-data", vm_key=100)

        assert file.name == "/user-data"

    def test_get_cloudinit_file_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting non-existent cloud-init file raises NotFoundError."""
        mock_session.request.return_value.status_code = 404
        mock_session.request.return_value.json.return_value = {"error": "Not found"}
        mock_session.request.return_value.text = "Not found"

        with pytest.raises(NotFoundError):
            mock_client.cloudinit_files.get(999)

    def test_get_cloudinit_file_no_params(self, mock_client: VergeClient) -> None:
        """Test getting cloud-init file without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or"):
            mock_client.cloudinit_files.get()

    def test_get_cloudinit_file_name_without_vm_key(self, mock_client: VergeClient) -> None:
        """Test getting cloud-init file by name without vm_key raises ValueError."""
        with pytest.raises(ValueError, match="vm_key is required"):
            mock_client.cloudinit_files.get(name="/user-data")

    def test_create_cloudinit_file(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a cloud-init file."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},  # POST response
            {  # GET response
                "$key": 1,
                "name": "/user-data",
                "owner": "vms/100",
                "render": "no",
                "filesize": 20,
            },
        ]

        file = mock_client.cloudinit_files.create(
            vm_key=100,
            name="/user-data",
            contents="#cloud-config\ntest: true",
            render="No",
        )

        assert file.name == "/user-data"
        assert file.render == "no"

    def test_create_cloudinit_file_with_jinja2(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a cloud-init file with Jinja2 render type."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "/user-data", "owner": "vms/100", "render": "jinja2"},
        ]

        mock_client.cloudinit_files.create(
            vm_key=100,
            name="/user-data",
            contents="{{ hostname }}",
            render="Jinja2",
        )

        # Verify render was set correctly in POST body
        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("render") == "jinja2"

    def test_create_cloudinit_file_with_variables(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a cloud-init file with Variables render type."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "/user-data", "owner": "vms/100", "render": "variables"},
        ]

        mock_client.cloudinit_files.create(
            vm_key=100,
            name="/user-data",
            contents="${vm_name}",
            render="Variables",
        )

        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("render") == "variables"

    def test_create_cloudinit_file_without_contents(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a cloud-init file without contents."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "/user-data", "owner": "vms/100", "filesize": 0},
        ]

        mock_client.cloudinit_files.create(
            vm_key=100,
            name="/user-data",
        )

        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert "contents" not in body

    def test_create_cloudinit_file_contents_too_large(
        self, mock_client: VergeClient
    ) -> None:
        """Test creating cloud-init file with contents exceeding max size raises ValueError."""
        large_contents = "x" * 65537  # > 64KB

        with pytest.raises(ValueError, match="exceed maximum size"):
            mock_client.cloudinit_files.create(
                vm_key=100,
                name="/user-data",
                contents=large_contents,
            )

    def test_update_cloudinit_file(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating a cloud-init file."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "/user-data",
            "owner": "vms/100",
            "render": "variables",
        }

        file = mock_client.cloudinit_files.update(1, render="Variables")

        assert file.render == "variables"

    def test_update_cloudinit_file_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating cloud-init file name."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "/new-user-data",
            "owner": "vms/100",
        }

        mock_client.cloudinit_files.update(1, name="/new-user-data")

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("name") == "/new-user-data"

    def test_update_cloudinit_file_contents(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating cloud-init file contents."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "/user-data",
            "owner": "vms/100",
            "filesize": 30,
        }

        new_contents = "#cloud-config\nnew: content"
        mock_client.cloudinit_files.update(1, contents=new_contents)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("contents") == new_contents

    def test_update_cloudinit_file_contents_too_large(
        self, mock_client: VergeClient
    ) -> None:
        """Test updating with contents exceeding max size raises ValueError."""
        large_contents = "x" * 65537

        with pytest.raises(ValueError, match="exceed maximum size"):
            mock_client.cloudinit_files.update(1, contents=large_contents)

    def test_update_cloudinit_file_no_changes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating cloud-init file with no changes returns current state."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "/user-data",
            "owner": "vms/100",
        }

        file = mock_client.cloudinit_files.update(1)

        assert file.key == 1

    def test_delete_cloudinit_file(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test deleting a cloud-init file."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.cloudinit_files.delete(1)

        # Verify DELETE was called
        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE"
        assert "cloudinit_files/1" in call_args.kwargs.get("url", "")

    def test_get_content(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting cloud-init file content."""
        mock_session.request.return_value.status_code = 200
        mock_session.request.return_value.content = b"#cloud-config\ntest: true"

        content = mock_client.cloudinit_files.get_content(1)

        assert content == "#cloud-config\ntest: true"
        # Verify download parameter was used
        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("params", {}).get("download") == 1

    def test_get_content_as_bytes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting cloud-init file content as bytes."""
        mock_session.request.return_value.status_code = 200
        mock_session.request.return_value.content = b"#cloud-config\ntest: true"

        content = mock_client.cloudinit_files.get_content(1, as_bytes=True)

        assert content == b"#cloud-config\ntest: true"
        assert isinstance(content, bytes)

    def test_get_content_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting content of non-existent file raises NotFoundError."""
        mock_session.request.return_value.status_code = 404

        with pytest.raises(NotFoundError):
            mock_client.cloudinit_files.get_content(999)

    def test_list_for_vm(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test list_for_vm convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},
            {"$key": 2, "name": "/meta-data", "owner": "vms/100"},
        ]

        files = mock_client.cloudinit_files.list_for_vm(100)

        assert len(files) == 2
        call_args = mock_session.request.call_args
        assert "owner eq 'vms/100'" in call_args.kwargs.get("params", {}).get("filter", "")


# =============================================================================
# CloudInitFile Object Method Tests
# =============================================================================


class TestCloudInitFileObjectMethods:
    """Unit tests for CloudInitFile object methods."""

    def test_get_content_via_object(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting content via file object."""
        mock_session.request.return_value.status_code = 200
        mock_session.request.return_value.content = b"#cloud-config\ntest: true"

        data = {"$key": 1, "name": "/user-data", "owner": "vms/100"}
        file = CloudInitFile(data, mock_client.cloudinit_files)

        content = file.get_content()

        assert content == "#cloud-config\ntest: true"

    def test_get_content_as_bytes_via_object(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting content as bytes via file object."""
        mock_session.request.return_value.status_code = 200
        mock_session.request.return_value.content = b"#cloud-config"

        data = {"$key": 1, "name": "/user-data", "owner": "vms/100"}
        file = CloudInitFile(data, mock_client.cloudinit_files)

        content = file.get_content(as_bytes=True)

        assert isinstance(content, bytes)

    def test_save_via_object(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating via file object save method."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "/user-data",
            "owner": "vms/100",
            "render": "jinja2",
        }

        data = {"$key": 1, "name": "/user-data", "owner": "vms/100", "render": "no"}
        file = CloudInitFile(data, mock_client.cloudinit_files)

        updated = file.save(render="Jinja2")

        assert updated.render == "jinja2"

    def test_delete_via_object(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test deleting via file object."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        data = {"$key": 1, "name": "/user-data", "owner": "vms/100"}
        file = CloudInitFile(data, mock_client.cloudinit_files)

        file.delete()

        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE"
        assert "cloudinit_files/1" in call_args.kwargs.get("url", "")


# =============================================================================
# Render Type Mapping Tests
# =============================================================================


class TestMappings:
    """Unit tests for mapping constants."""

    def test_render_type_map(self) -> None:
        """Test RENDER_TYPE_MAP contains all render types."""
        assert "No" in RENDER_TYPE_MAP
        assert "Variables" in RENDER_TYPE_MAP
        assert "Jinja2" in RENDER_TYPE_MAP

        assert RENDER_TYPE_MAP["No"] == "no"
        assert RENDER_TYPE_MAP["Variables"] == "variables"
        assert RENDER_TYPE_MAP["Jinja2"] == "jinja2"

    def test_render_type_display(self) -> None:
        """Test RENDER_TYPE_DISPLAY contains all render types."""
        assert "no" in RENDER_TYPE_DISPLAY
        assert "variables" in RENDER_TYPE_DISPLAY
        assert "jinja2" in RENDER_TYPE_DISPLAY

        assert RENDER_TYPE_DISPLAY["no"] == "No"
        assert RENDER_TYPE_DISPLAY["variables"] == "Variables"
        assert RENDER_TYPE_DISPLAY["jinja2"] == "Jinja2"
