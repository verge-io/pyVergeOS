#!/usr/bin/env python3
"""Example: API key management with pyvergeos.

This example demonstrates API key operations including:
- Listing and filtering API keys
- Creating API keys with various options
- Expiration settings
- IP restrictions
- Deleting API keys

IMPORTANT: The API key secret is only shown ONCE at creation time.
Store it securely immediately - it cannot be retrieved later!
"""

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def list_api_keys() -> None:
    """Demonstrate listing API keys."""
    print("=== List API Keys ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # List all API keys
        api_keys = client.api_keys.list()
        print(f"Found {len(api_keys)} API keys:")

        for key in api_keys:
            expires = key.expires_datetime or "Never"
            last_used = key.last_login_datetime or "Never"
            print(f"  - {key.name}")
            print(f"    Key: {key.key}")
            print(f"    User: {key.user_name}")
            print(f"    Description: {key.description or '(not set)'}")
            print(f"    Expires: {expires}")
            print(f"    Last Used: {last_used}")
            if key.ip_allow_list:
                print(f"    IP Allow: {', '.join(key.ip_allow_list)}")
            if key.ip_deny_list:
                print(f"    IP Deny: {', '.join(key.ip_deny_list)}")
            print()


def list_keys_for_user() -> None:
    """List API keys for a specific user."""
    print("\n=== List Keys for User ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # List by username
        keys = client.api_keys.list(user="admin")
        print(f"API keys for admin ({len(keys)}):")
        for key in keys:
            print(f"  - {key.name} (created: {key.created_datetime})")

        # Or list by user key
        admin = client.users.get(name="admin")
        keys = client.api_keys.list(user=admin.key)
        print(f"\nAPI keys for user key {admin.key} ({len(keys)}):")
        for key in keys:
            print(f"  - {key.name}")


def get_api_key() -> None:
    """Get a specific API key by key ID or name."""
    print("\n=== Get API Key ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            # Get by name (requires user parameter)
            key = client.api_keys.get(name="automation", user="admin")
            print(f"Found key: {key.name}")
            print(f"  Description: {key.description}")
            print(f"  Created: {key.created_datetime}")
            print(f"  Expires: {key.expires_datetime or 'Never'}")
            print(f"  Is Expired: {key.is_expired}")
        except NotFoundError:
            print("API key not found")


def create_basic_api_key() -> None:
    """Create a basic API key that never expires."""
    print("\n=== Create Basic API Key ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Create an API key
        result = client.api_keys.create(
            user="admin",
            name="my-automation-key",
            description="Key for automation scripts",
        )

        print(f"Created API key: {result.name}")
        print(f"  Key ID: {result.key}")
        print(f"  User: {result.user_name}")
        print()
        print("  *** IMPORTANT: Save this secret NOW! ***")
        print(f"  Secret: {result.secret}")
        print("  *** It cannot be retrieved later! ***")

        # Clean up for demo
        # client.api_keys.delete(result.key)


def create_key_with_expiration() -> None:
    """Create API keys with various expiration settings."""
    print("\n=== Create Keys with Expiration ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Create key that expires in 30 days
        result = client.api_keys.create(
            user="admin",
            name="30-day-key",
            description="Expires in 30 days",
            expires_in="30d",  # Supports: d (days), w (weeks), m (months), y (years)
        )
        print(f"Created 30-day key: {result.name}")
        print(f"  Secret: {result.secret}")

        # Verify expiration
        key = client.api_keys.get(result.key)
        print(f"  Expires: {key.expires_datetime}")

        # Clean up
        client.api_keys.delete(result.key)

        # Create key that expires in 1 week
        result = client.api_keys.create(
            user="admin",
            name="1-week-key",
            expires_in="1w",
        )
        print(f"\nCreated 1-week key: {result.name}")
        key = client.api_keys.get(result.key)
        print(f"  Expires: {key.expires_datetime}")

        # Clean up
        client.api_keys.delete(result.key)

        # Create key with specific expiration date
        from datetime import datetime, timedelta, timezone

        expiration = datetime.now(tz=timezone.utc) + timedelta(days=90)
        result = client.api_keys.create(
            user="admin",
            name="specific-date-key",
            expires=expiration,
        )
        print(f"\nCreated key with specific expiration: {result.name}")
        key = client.api_keys.get(result.key)
        print(f"  Expires: {key.expires_datetime}")

        # Clean up
        client.api_keys.delete(result.key)


def create_key_with_ip_restrictions() -> None:
    """Create API keys with IP-based access restrictions."""
    print("\n=== Create Keys with IP Restrictions ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Create key with IP allowlist
        result = client.api_keys.create(
            user="admin",
            name="restricted-key",
            description="Only accessible from specific IPs",
            ip_allow_list=[
                "10.0.0.0/8",  # Allow all 10.x.x.x
                "192.168.1.100",  # Allow specific IP
            ],
        )
        print(f"Created restricted key: {result.name}")
        print(f"  Secret: {result.secret}")

        # Verify restrictions
        key = client.api_keys.get(result.key)
        print(f"  IP Allow List: {key.ip_allow_list}")

        # Clean up
        client.api_keys.delete(result.key)

        # Create key with both allow and deny lists
        result = client.api_keys.create(
            user="admin",
            name="complex-rules-key",
            description="Allow subnet but deny specific hosts",
            ip_allow_list=["10.0.0.0/8"],
            ip_deny_list=["10.0.0.1", "10.0.0.2"],  # Deny specific IPs in allowed range
        )
        print(f"\nCreated key with complex rules: {result.name}")
        key = client.api_keys.get(result.key)
        print(f"  IP Allow List: {key.ip_allow_list}")
        print(f"  IP Deny List: {key.ip_deny_list}")

        # Clean up
        client.api_keys.delete(result.key)


def delete_api_key() -> None:
    """Demonstrate deleting API keys."""
    print("\n=== Delete API Keys ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Create a test key
        result = client.api_keys.create(
            user="admin",
            name="temp-delete-test",
        )
        print(f"Created key: {result.name} (ID: {result.key})")

        # Method 1: Delete via manager
        client.api_keys.delete(result.key)
        print("Deleted via manager.delete()")

        # Create another key
        result = client.api_keys.create(
            user="admin",
            name="temp-delete-test-2",
        )
        print(f"\nCreated key: {result.name} (ID: {result.key})")

        # Method 2: Delete via object method
        key = client.api_keys.get(result.key)
        key.delete()
        print("Deleted via key.delete()")


def api_key_workflow() -> None:
    """Complete workflow: create key, use it, then rotate."""
    print("\n=== API Key Workflow ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Step 1: Create a new API key
        print("Step 1: Creating new API key...")
        result = client.api_keys.create(
            user="admin",
            name="workflow-demo-key",
            description="Demonstration of API key workflow",
            expires_in="90d",
        )
        print(f"  Created: {result.name}")
        print(f"  Secret: {result.secret}")
        print("  (In production, store this secret securely!)")

        # Step 2: The secret would be used in another application
        print("\nStep 2: Key can now be used for authentication")
        print(f"  Use token '{result.secret}' for Bearer auth")

        # Step 3: Check key usage
        key = client.api_keys.get(result.key)
        print("\nStep 3: Key status")
        print(f"  Last used: {key.last_login_datetime or 'Never'}")
        print(f"  Last IP: {key.last_login_ip or 'N/A'}")
        print(f"  Expires: {key.expires_datetime}")

        # Step 4: Rotate key (create new, delete old)
        print("\nStep 4: Rotating key...")
        new_result = client.api_keys.create(
            user="admin",
            name="workflow-demo-key-v2",
            description="Rotated key",
            expires_in="90d",
        )
        print(f"  Created new key: {new_result.name}")
        print(f"  New secret: {new_result.secret}")

        # Delete old key
        client.api_keys.delete(result.key)
        print(f"  Deleted old key: {result.name}")

        # Clean up demo
        client.api_keys.delete(new_result.key)
        print("\n(Cleaned up demo keys)")


if __name__ == "__main__":
    print("pyvergeos API Key Management Examples")
    print("=" * 45)
    print()
    print("NOTE: Update host/credentials in this file before running.")
    print()
    print("IMPORTANT: API key secrets are only shown ONCE at creation!")
    print("           Store them securely immediately!")
    print()

    # Uncomment the examples you want to run:
    # list_api_keys()
    # list_keys_for_user()
    # get_api_key()
    # create_basic_api_key()
    # create_key_with_expiration()
    # create_key_with_ip_restrictions()
    # delete_api_key()
    # api_key_workflow()

    print("See the code for examples of:")
    print("  - Listing and filtering API keys")
    print("  - Getting API keys by ID or name")
    print("  - Creating keys (basic, with expiration, with IP restrictions)")
    print("  - Deleting API keys")
    print("  - Complete API key workflow (create, use, rotate)")
