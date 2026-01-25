#!/usr/bin/env python3
"""Example: Connection management with pyvergeos.

This example demonstrates various ways to connect to a VergeOS system.
"""

import os

from pyvergeos import VergeClient
from pyvergeos.exceptions import AuthenticationError, VergeConnectionError


def basic_connection() -> None:
    """Connect using username and password."""
    print("=== Basic Connection ===")

    client = VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,  # Set to True in production with valid certs
    )

    print(f"Connected: {client.is_connected}")
    print(f"VergeOS Version: {client.version}")

    # Always disconnect when done
    client.disconnect()
    print(f"Disconnected: {not client.is_connected}")


def token_connection() -> None:
    """Connect using an API token."""
    print("\n=== Token Connection ===")

    client = VergeClient(
        host="192.168.1.100",
        token="your-api-token",
        verify_ssl=False,
    )

    print(f"Connected: {client.is_connected}")
    print(f"VergeOS Version: {client.version}")

    client.disconnect()


def context_manager() -> None:
    """Use context manager for automatic cleanup."""
    print("\n=== Context Manager ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        print(f"Inside context: Connected = {client.is_connected}")
        print(f"VergeOS Version: {client.version}")

    # Client is automatically disconnected when exiting the 'with' block
    print(f"After context: Connected = {client.is_connected}")


def from_environment() -> None:
    """Connect using environment variables."""
    print("\n=== From Environment Variables ===")

    # Set environment variables (typically done outside the script)
    os.environ["VERGE_HOST"] = "192.168.1.100"
    os.environ["VERGE_USERNAME"] = "admin"
    os.environ["VERGE_PASSWORD"] = "your-password"
    os.environ["VERGE_VERIFY_SSL"] = "false"
    os.environ["VERGE_TIMEOUT"] = "60"

    # Create client from environment
    client = VergeClient.from_env()

    print(f"Connected: {client.is_connected}")
    print(f"VergeOS Version: {client.version}")

    client.disconnect()


def error_handling() -> None:
    """Demonstrate connection error handling."""
    print("\n=== Error Handling ===")

    # Invalid host
    try:
        VergeClient(
            host="invalid.example.com",
            username="admin",
            password="secret",
            timeout=5,
        )
    except VergeConnectionError as e:
        print(f"Connection failed: {e}")

    # Invalid credentials
    try:
        VergeClient(
            host="192.168.1.100",
            username="admin",
            password="wrong-password",
            verify_ssl=False,
        )
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")


def deferred_connection() -> None:
    """Create client without immediate connection."""
    print("\n=== Deferred Connection ===")

    # Create client but don't connect yet
    client = VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
        auto_connect=False,  # Don't connect immediately
    )

    print(f"After init: Connected = {client.is_connected}")

    # Connect when ready
    client.connect()
    print(f"After connect(): Connected = {client.is_connected}")

    client.disconnect()


if __name__ == "__main__":
    print("pyvergeos Connection Examples")
    print("=" * 40)
    print()
    print("NOTE: Update host/credentials in this file before running.")
    print()

    # Uncomment the examples you want to run:
    # basic_connection()
    # token_connection()
    # context_manager()
    # from_environment()
    # error_handling()
    # deferred_connection()

    print("\nSee the code for examples of:")
    print("  - Basic username/password connection")
    print("  - API token connection")
    print("  - Context manager (with statement)")
    print("  - Environment variable configuration")
    print("  - Error handling")
    print("  - Deferred connection")
