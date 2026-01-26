"""Unit tests for NAS volume browser."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import APIError, NotFoundError, VergeTimeoutError
from pyvergeos.resources.nas_volume_browser import (
    NASVolumeFile,
    NASVolumeFileManager,
    _format_file_size,
)
from pyvergeos.resources.nas_volumes import NASVolume, NASVolumeManager


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def file_manager(mock_client):
    """Create a NASVolumeFileManager with mock client."""
    return NASVolumeFileManager(
        mock_client,
        volume_key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        volume_name="TestVolume",
    )


@pytest.fixture
def sample_file_entry():
    """Sample file entry from API."""
    return {
        "name": "document.pdf",
        "n_name": "document.pdf",
        "size": 102400,
        "date": 1737792000,
        "type": "file",
    }


@pytest.fixture
def sample_directory_entry():
    """Sample directory entry from API."""
    return {
        "name": "images",
        "n_name": "images",
        "size": 4096,
        "date": 1737705600,
        "type": "directory",
    }


@pytest.fixture
def sample_browse_result(sample_file_entry, sample_directory_entry):
    """Sample browse result containing files and directories."""
    return [sample_file_entry, sample_directory_entry]


class TestNASVolumeFile:
    """Tests for NASVolumeFile model."""

    def test_init(self, sample_file_entry):
        """Test file initialization."""
        file = NASVolumeFile(sample_file_entry)
        assert file["name"] == "document.pdf"
        assert file["size"] == 102400
        assert file["type"] == "file"

    def test_name_property(self, sample_file_entry):
        """Test name property."""
        file = NASVolumeFile(sample_file_entry)
        assert file.name == "document.pdf"

    def test_is_file_property(self, sample_file_entry):
        """Test is_file property for file entry."""
        file = NASVolumeFile(sample_file_entry)
        assert file.is_file is True
        assert file.is_directory is False

    def test_is_directory_property(self, sample_directory_entry):
        """Test is_directory property for directory entry."""
        directory = NASVolumeFile(sample_directory_entry)
        assert directory.is_directory is True
        assert directory.is_file is False

    def test_size_property(self, sample_file_entry):
        """Test size property."""
        file = NASVolumeFile(sample_file_entry)
        assert file.size == 102400

    def test_size_display_property(self, sample_file_entry):
        """Test size_display property."""
        file = NASVolumeFile(sample_file_entry)
        assert file.size_display == "100.00 KB"

    def test_modified_property(self, sample_file_entry):
        """Test modified property."""
        file = NASVolumeFile(sample_file_entry)
        modified = file.modified
        assert modified is not None
        assert isinstance(modified, datetime)
        assert modified.tzinfo == timezone.utc

    def test_modified_property_none(self):
        """Test modified property when date is missing."""
        file = NASVolumeFile({"name": "test", "type": "file"})
        assert file.modified is None

    def test_full_path_property(self):
        """Test full_path property."""
        file = NASVolumeFile(
            {
                "name": "test.txt",
                "type": "file",
                "_full_path": "/documents/test.txt",
            }
        )
        assert file.full_path == "/documents/test.txt"

    def test_full_path_default(self, sample_file_entry):
        """Test full_path default when _full_path not set."""
        file = NASVolumeFile(sample_file_entry)
        assert file.full_path == "/document.pdf"

    def test_volume_key_property(self, sample_file_entry):
        """Test volume_key property."""
        sample_file_entry["_volume_key"] = "abc123"
        file = NASVolumeFile(sample_file_entry)
        assert file.volume_key == "abc123"

    def test_attribute_access(self, sample_file_entry):
        """Test attribute-style access to dict items."""
        file = NASVolumeFile(sample_file_entry)
        assert file.name == "document.pdf"
        assert file.n_name == "document.pdf"

    def test_attribute_error(self, sample_file_entry):
        """Test AttributeError for missing attribute."""
        file = NASVolumeFile(sample_file_entry)
        with pytest.raises(AttributeError, match="has no attribute 'nonexistent'"):
            _ = file.nonexistent

    def test_dict_behavior(self, sample_file_entry):
        """Test dict-like behavior."""
        file = NASVolumeFile(sample_file_entry)
        assert "name" in file
        assert file.get("nonexistent", "default") == "default"
        assert list(file.keys()) == list(sample_file_entry.keys())


class TestNASVolumeFileManager:
    """Tests for NASVolumeFileManager."""

    def test_init(self, mock_client):
        """Test manager initialization."""
        manager = NASVolumeFileManager(
            mock_client,
            volume_key="abc123",
            volume_name="TestVol",
        )
        assert manager._volume_key == "abc123"
        assert manager._volume_name == "TestVol"
        assert manager._client == mock_client

    def test_list_root(self, file_manager, mock_client, sample_browse_result):
        """Test listing root directory."""
        # Setup mock responses
        mock_client._request.side_effect = [
            # POST response (create job)
            {"$key": "job123", "location": "/v4/volume_browser/job123"},
            # GET response (poll for result)
            {"id": "job123", "status": "complete", "result": sample_browse_result},
        ]

        files = file_manager.list("/")

        assert len(files) == 2
        assert files[0].name == "document.pdf"
        assert files[0].is_file
        assert files[1].name == "images"
        assert files[1].is_directory

        # Verify POST was called with correct payload
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert post_call[0][1] == "volume_browser"
        payload = post_call[1]["json_data"]
        assert payload["volume"] == file_manager._volume_key
        assert payload["query"] == "get-dir"
        assert payload["params"]["dir"] == ""  # Root is empty string, not "/"

    def test_list_subdirectory(self, file_manager, mock_client, sample_browse_result):
        """Test listing a subdirectory."""
        mock_client._request.side_effect = [
            {"$key": "job456"},
            {"id": "job456", "status": "complete", "result": sample_browse_result},
        ]

        files = file_manager.list("/documents")

        # Verify the dir param was set correctly (without leading slash)
        post_call = mock_client._request.call_args_list[0]
        payload = post_call[1]["json_data"]
        assert payload["params"]["dir"] == "documents"

        # Verify full_path includes the parent directory
        assert files[0].full_path == "/documents/document.pdf"

    def test_list_empty_directory(self, file_manager, mock_client):
        """Test listing an empty directory."""
        mock_client._request.side_effect = [
            {"$key": "job789"},
            {"id": "job789", "status": "complete", "result": None},
        ]

        files = file_manager.list("/empty")

        assert files == []

    def test_list_with_pagination(self, file_manager, mock_client, sample_browse_result):
        """Test listing with limit and offset."""
        mock_client._request.side_effect = [
            {"$key": "job111"},
            {"id": "job111", "status": "complete", "result": sample_browse_result},
        ]

        file_manager.list("/", limit=10, offset=5)

        post_call = mock_client._request.call_args_list[0]
        payload = post_call[1]["json_data"]
        assert payload["params"]["limit"] == 10
        assert payload["params"]["offset"] == 5

    def test_list_with_extensions_filter(self, file_manager, mock_client, sample_browse_result):
        """Test listing with extensions filter."""
        mock_client._request.side_effect = [
            {"$key": "job222"},
            {"id": "job222", "status": "complete", "result": sample_browse_result},
        ]

        file_manager.list("/", extensions="pdf,doc")

        post_call = mock_client._request.call_args_list[0]
        payload = post_call[1]["json_data"]
        assert payload["params"]["filter"]["extensions"] == "pdf,doc"

    def test_list_polls_until_complete(self, file_manager, mock_client, sample_browse_result):
        """Test that list polls until status is complete."""
        mock_client._request.side_effect = [
            {"$key": "job333"},
            {"id": "job333", "status": "running"},
            {"id": "job333", "status": "running"},
            {"id": "job333", "status": "complete", "result": sample_browse_result},
        ]

        with patch("time.sleep"):  # Don't actually sleep in tests
            files = file_manager.list("/")

        assert len(files) == 2
        # Should have called _request 4 times (1 POST + 3 GETs)
        assert mock_client._request.call_count == 4

    def test_list_timeout(self, file_manager, mock_client):
        """Test timeout when browse operation takes too long."""
        mock_client._request.side_effect = [
            {"$key": "job444"},
        ] + [{"id": "job444", "status": "running"}] * 100  # Always running

        with patch("time.sleep"), pytest.raises(VergeTimeoutError, match="timed out"):
            file_manager.list("/", timeout=5)

    def test_list_error_status(self, file_manager, mock_client):
        """Test handling error status from browse operation."""
        mock_client._request.side_effect = [
            {"$key": "job555"},
            {"id": "job555", "status": "error", "result": "Volume not found"},
        ]

        with patch("time.sleep"), pytest.raises(APIError, match="Volume not found"):
            file_manager.list("/")

    def test_list_no_job_key(self, file_manager, mock_client):
        """Test handling missing job key in response."""
        # Return a dict without $key or id
        mock_client._request.return_value = {"location": "/v4/volume_browser/"}

        with pytest.raises(APIError, match="No job key"):
            file_manager.list("/")

    def test_list_no_response(self, file_manager, mock_client):
        """Test handling no response from API."""
        mock_client._request.return_value = None

        with pytest.raises(APIError, match="No response"):
            file_manager.list("/")

    def test_list_result_as_string(self, file_manager, mock_client, sample_browse_result):
        """Test handling result that is a JSON string."""
        import json

        mock_client._request.side_effect = [
            {"$key": "job666"},
            {"id": "job666", "status": "complete", "result": json.dumps(sample_browse_result)},
        ]

        with patch("time.sleep"):
            files = file_manager.list("/")

        assert len(files) == 2

    def test_list_result_with_entries_property(
        self, file_manager, mock_client, sample_browse_result
    ):
        """Test handling result with entries property."""
        mock_client._request.side_effect = [
            {"$key": "job777"},
            {"id": "job777", "status": "complete", "result": {"entries": sample_browse_result}},
        ]

        with patch("time.sleep"):
            files = file_manager.list("/")

        assert len(files) == 2

    def test_get_file(self, file_manager, mock_client, sample_browse_result):
        """Test getting a specific file."""
        mock_client._request.side_effect = [
            {"$key": "job888"},
            {"id": "job888", "status": "complete", "result": sample_browse_result},
        ]

        with patch("time.sleep"):
            file = file_manager.get("/document.pdf")

        assert file.name == "document.pdf"
        assert file.is_file

    def test_get_directory(self, file_manager, mock_client, sample_browse_result):
        """Test getting a specific directory."""
        mock_client._request.side_effect = [
            {"$key": "job999"},
            {"id": "job999", "status": "complete", "result": sample_browse_result},
        ]

        with patch("time.sleep"):
            directory = file_manager.get("/images")

        assert directory.name == "images"
        assert directory.is_directory

    def test_get_nested_path(self, file_manager, mock_client, sample_file_entry):
        """Test getting a file from a nested path."""
        mock_client._request.side_effect = [
            {"$key": "jobaaa"},
            {"id": "jobaaa", "status": "complete", "result": [sample_file_entry]},
        ]

        with patch("time.sleep"):
            file_manager.get("/documents/reports/document.pdf")

        # Verify it browsed the parent directory
        post_call = mock_client._request.call_args_list[0]
        payload = post_call[1]["json_data"]
        assert payload["params"]["dir"] == "documents/reports"

    def test_get_not_found(self, file_manager, mock_client, sample_browse_result):
        """Test getting a file that doesn't exist."""
        mock_client._request.side_effect = [
            {"$key": "jobbbb"},
            {"id": "jobbbb", "status": "complete", "result": sample_browse_result},
        ]

        with patch("time.sleep"), pytest.raises(NotFoundError, match="not found"):
            file_manager.get("/nonexistent.txt")

    def test_get_from_empty_directory(self, file_manager, mock_client):
        """Test getting a file from an empty directory."""
        mock_client._request.side_effect = [
            {"$key": "jobccc"},
            {"id": "jobccc", "status": "complete", "result": None},
        ]

        with patch("time.sleep"), pytest.raises(NotFoundError, match="not found"):
            file_manager.get("/empty/test.txt")


class TestFormatFileSize:
    """Tests for _format_file_size helper function."""

    def test_zero_bytes(self):
        """Test formatting zero bytes."""
        assert _format_file_size(0) == "0 B"

    def test_bytes(self):
        """Test formatting small byte values."""
        assert _format_file_size(1) == "1 B"
        assert _format_file_size(512) == "512 B"
        assert _format_file_size(1023) == "1023 B"

    def test_kilobytes(self):
        """Test formatting kilobyte values."""
        assert _format_file_size(1024) == "1.00 KB"
        assert _format_file_size(1536) == "1.50 KB"
        assert _format_file_size(102400) == "100.00 KB"

    def test_megabytes(self):
        """Test formatting megabyte values."""
        assert _format_file_size(1048576) == "1.00 MB"
        assert _format_file_size(5242880) == "5.00 MB"

    def test_gigabytes(self):
        """Test formatting gigabyte values."""
        assert _format_file_size(1073741824) == "1.00 GB"
        assert _format_file_size(10737418240) == "10.00 GB"

    def test_terabytes(self):
        """Test formatting terabyte values."""
        assert _format_file_size(1099511627776) == "1.00 TB"


class TestNASVolumeFilesProperty:
    """Tests for NASVolume.files property."""

    def test_files_property_returns_manager(self, mock_client):
        """Test that files property returns a NASVolumeFileManager."""
        # Create a NASVolume with mock data
        vol_manager = NASVolumeManager(mock_client)
        vol_data = {
            "$key": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            "name": "TestVolume",
        }
        volume = NASVolume(vol_data, vol_manager)

        file_manager = volume.files

        assert isinstance(file_manager, NASVolumeFileManager)
        assert file_manager._volume_key == volume.key
        assert file_manager._volume_name == "TestVolume"


class TestNASVolumeManagerFiles:
    """Tests for NASVolumeManager.files method."""

    def test_files_method_returns_manager(self, mock_client):
        """Test that files method returns a NASVolumeFileManager."""
        vol_manager = NASVolumeManager(mock_client)

        file_manager = vol_manager.files(
            "8f73f8bcc9c9f1aaba32f733bfc295acaf548554", name="TestVolume"
        )

        assert isinstance(file_manager, NASVolumeFileManager)
        assert file_manager._volume_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
        assert file_manager._volume_name == "TestVolume"

    def test_files_method_without_name(self, mock_client):
        """Test files method without optional name parameter."""
        vol_manager = NASVolumeManager(mock_client)

        file_manager = vol_manager.files("abc123")

        assert file_manager._volume_key == "abc123"
        assert file_manager._volume_name is None
