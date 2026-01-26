"""Unit tests for File operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.files import File


class TestFileManager:
    """Unit tests for FileManager."""

    def test_list_files(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing files."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "ubuntu.iso",
                "type": "iso",
                "filesize": 3617587200,
                "allocated_bytes": 3617587200,
                "used_bytes": 3610116096,
                "preferred_tier": "1",
                "modified": 1734465618,
                "creator": "admin",
            },
            {
                "$key": 2,
                "name": "disk.qcow2",
                "type": "qcow2",
                "filesize": 53687091200,
                "allocated_bytes": 53687091200,
                "used_bytes": 4194304,
                "preferred_tier": "3",
                "modified": 1734465700,
                "creator": "admin",
            },
        ]

        files = mock_client.files.list()

        assert len(files) == 2
        assert files[0].name == "ubuntu.iso"
        assert files[0].file_type == "iso"
        assert files[1].name == "disk.qcow2"
        assert files[1].file_type == "qcow2"

    def test_list_files_by_type(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test filtering files by type."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "ubuntu.iso", "type": "iso"},
            {"$key": 2, "name": "disk.qcow2", "type": "qcow2"},
            {"$key": 3, "name": "server.iso", "type": "iso"},
        ]

        # Filter by single type
        files = mock_client.files.list(file_type="iso")
        assert len(files) == 2
        assert all(f.file_type == "iso" for f in files)

        # Filter by multiple types
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "ubuntu.iso", "type": "iso"},
            {"$key": 2, "name": "disk.qcow2", "type": "qcow2"},
            {"$key": 3, "name": "vm.ova", "type": "ova"},
        ]
        files = mock_client.files.list(file_type=["iso", "qcow2"])
        assert len(files) == 2

    def test_get_file_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a file by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 42,
            "name": "test.iso",
            "type": "iso",
            "filesize": 1073741824,
        }

        file = mock_client.files.get(42)

        assert file.key == 42
        assert file.name == "test.iso"
        assert file.file_type == "iso"
        assert file.size_bytes == 1073741824

    def test_get_file_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a file by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 99,
                "name": "my-image.qcow2",
                "type": "qcow2",
            }
        ]

        file = mock_client.files.get(name="my-image.qcow2")

        assert file.name == "my-image.qcow2"
        assert file.key == 99

    def test_get_file_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that NotFoundError is raised when file not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.files.get(name="nonexistent.iso")

    def test_delete_file(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a file."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.files.delete(42)

        # Verify the DELETE request was made
        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE"
        assert "files/42" in call_args.kwargs.get("url")


class TestFile:
    """Unit tests for File model."""

    def test_file_properties(self, mock_client: VergeClient) -> None:
        """Test File property accessors."""
        data = {
            "$key": 1,
            "name": "ubuntu-22.04.iso",
            "type": "iso",
            "description": "Ubuntu Server",
            "filesize": 3617587200,
            "allocated_bytes": 3617587200,
            "used_bytes": 3610116096,
            "preferred_tier": "2",
            "modified": 1734465618,
            "creator": "admin",
        }
        file = File(data, mock_client.files)

        assert file.key == 1
        assert file.name == "ubuntu-22.04.iso"
        assert file.file_type == "iso"
        assert file.type_display == "ISO"
        assert file.description == "Ubuntu Server"
        assert file.size_bytes == 3617587200
        assert file.size_gb == pytest.approx(3.369, abs=0.01)
        assert file.allocated_bytes == 3617587200
        assert file.used_bytes == 3610116096
        assert file.preferred_tier == 2
        assert file.creator == "admin"
        assert file.modified is not None

    def test_file_size_conversions(self, mock_client: VergeClient) -> None:
        """Test file size conversions to GB."""
        data = {
            "$key": 1,
            "name": "large.qcow2",
            "type": "qcow2",
            "filesize": 107374182400,  # 100 GB
            "allocated_bytes": 107374182400,
            "used_bytes": 10737418240,  # 10 GB
        }
        file = File(data, mock_client.files)

        assert file.size_gb == 100.0
        assert file.allocated_gb == 100.0
        assert file.used_gb == 10.0

    def test_file_missing_fields(self, mock_client: VergeClient) -> None:
        """Test File handles missing fields gracefully."""
        data = {
            "$key": 1,
            "name": "minimal.iso",
        }
        file = File(data, mock_client.files)

        assert file.name == "minimal.iso"
        assert file.file_type == "unknown"
        assert file.description == ""
        assert file.size_bytes == 0
        assert file.size_gb == 0.0
        assert file.preferred_tier is None
        assert file.modified is None
        assert file.creator == ""

    def test_file_repr(self, mock_client: VergeClient) -> None:
        """Test File string representation."""
        data = {"$key": 42, "name": "test.iso", "type": "iso"}
        file = File(data, mock_client.files)

        repr_str = repr(file)
        assert "File" in repr_str
        assert "42" in repr_str
        assert "test.iso" in repr_str
        assert "iso" in repr_str
