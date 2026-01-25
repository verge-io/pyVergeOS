"""Pytest fixtures for pyvergeos tests."""

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient


@pytest.fixture
def mock_response() -> MagicMock:
    """Create a mock response object."""
    response = MagicMock()
    response.status_code = 200
    response.text = "{}"
    response.json.return_value = {}
    return response


@pytest.fixture
def mock_session(mock_response: MagicMock) -> Generator[MagicMock, None, None]:
    """Create a mock requests session."""
    with patch("pyvergeos.connection.requests.Session") as mock:
        session = MagicMock()
        session.request.return_value = mock_response
        mock.return_value = session
        yield session


@pytest.fixture
def mock_client(mock_session: MagicMock) -> VergeClient:
    """Create a VergeClient with mocked HTTP session.

    Use this for unit tests that don't need real API calls.
    """
    # Mock the system validation response
    mock_session.request.return_value.json.return_value = {
        "$key": 1,
        "yb_version": "4.12.0",
        "os_version": "26.0",
        "cloud_name": "test-cloud",
    }

    client = VergeClient(
        host="test.example.com",
        username="admin",
        password="secret",
        verify_ssl=False,
    )
    return client


@pytest.fixture
def sample_vm_data() -> dict[str, Any]:
    """Sample VM data for tests."""
    return {
        "$key": 123,
        "name": "test-vm",
        "ram": 2048,
        "cpu_cores": 2,
        "os_family": "linux",
        "powerstate": False,
        "is_snapshot": False,
        "machine": 456,
        "description": "Test VM",
    }


@pytest.fixture
def sample_network_data() -> dict[str, Any]:
    """Sample network data for tests."""
    return {
        "$key": 100,
        "name": "test-network",
        "type": "internal",
        "network": "192.168.1.0/24",
        "ipaddress": "192.168.1.1",
        "gateway": "192.168.1.254",
        "running": True,
        "status": "running",
        "dhcp_enabled": True,
        "dhcp_start": "192.168.1.100",
        "dhcp_stop": "192.168.1.200",
        "need_fw_apply": False,
        "need_dns_apply": False,
        "need_restart": False,
        "description": "Test network",
    }


@pytest.fixture
def live_client() -> Generator[VergeClient, None, None]:
    """Create a live client for integration tests.

    Requires environment variables:
    - VERGE_HOST
    - VERGE_USERNAME
    - VERGE_PASSWORD

    Skip if not configured.
    """
    host = os.environ.get("VERGE_HOST")
    username = os.environ.get("VERGE_USERNAME")
    password = os.environ.get("VERGE_PASSWORD")

    if not all([host, username, password]):
        pytest.skip("Live VergeOS credentials not configured")

    client = VergeClient(
        host=host,  # type: ignore[arg-type]
        username=username,
        password=password,
        verify_ssl=False,
    )

    yield client

    client.disconnect()
