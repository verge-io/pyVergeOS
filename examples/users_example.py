#!/usr/bin/env python3
"""Example: User management with pyvergeos.

This example demonstrates user operations including:
- Listing and filtering users
- Creating users with various options
- Updating user settings
- Enable/disable operations
- User type management (Normal, API, VDI)
"""

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def list_users() -> None:
    """Demonstrate listing users with various filters."""
    print("=== List Users ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # List all users (excludes system users by default)
        users = client.users.list()
        print(f"Found {len(users)} users:")

        for user in users:
            status = "Enabled" if user.is_enabled else "Disabled"
            print(f"  - {user.name}")
            print(f"    Key: {user.key}")
            print(f"    Type: {user.user_type_display}")
            print(f"    Status: {status}")
            print(f"    Display Name: {user.displayname or '(not set)'}")
            print(f"    Email: {user.email or '(not set)'}")
            print()


def list_by_type() -> None:
    """List users by type."""
    print("\n=== List by Type ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # List API users
        api_users = client.users.list_api_users()
        print(f"API Users ({len(api_users)}):")
        for user in api_users:
            print(f"  - {user.name}")

        # List VDI users
        vdi_users = client.users.list_vdi_users()
        print(f"VDI Users ({len(vdi_users)}):")
        for user in vdi_users:
            print(f"  - {user.name}")

        # List enabled users
        enabled = client.users.list_enabled()
        print(f"Enabled Users ({len(enabled)}):")
        for user in enabled[:5]:  # Show first 5
            print(f"  - {user.name}")

        # List disabled users
        disabled = client.users.list_disabled()
        print(f"Disabled Users ({len(disabled)}):")
        for user in disabled[:5]:
            print(f"  - {user.name}")


def get_user() -> None:
    """Get a specific user by name or key."""
    print("\n=== Get User ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            # Get by name
            user = client.users.get(name="admin")
            print(f"Found user: {user.name}")
            print(f"  Key: {user.key}")
            print(f"  Type: {user.user_type_display}")
            print(f"  Enabled: {user.is_enabled}")
            print(f"  Physical Access: {user.physical_access}")
            print(f"  2FA Enabled: {user.two_factor_enabled}")
            print(f"  2FA Type: {user.two_factor_type_display}")
            print(f"  Created: {user.created}")
            print(f"  Last Login: {user.last_login}")
            print(f"  Failed Attempts: {user.failed_attempts}")
            print(f"  Is Locked: {user.is_locked}")
        except NotFoundError:
            print("User not found")


def create_normal_user() -> None:
    """Create a standard user account."""
    print("\n=== Create Normal User ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Create a basic user
        user = client.users.create(
            name="jsmith",
            password="SecurePass123!",
            displayname="John Smith",
            email="jsmith@company.com",
        )

        print(f"Created user: {user.name}")
        print(f"  Key: {user.key}")
        print(f"  Display Name: {user.displayname}")
        print(f"  Email: {user.email}")

        # Cleanup for demo
        # client.users.delete(user.key)


def create_api_user() -> None:
    """Create an API user for automation."""
    print("\n=== Create API User ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Create an API user
        user = client.users.create(
            name="automation_service",
            password="ApiSecret123!",
            user_type="api",
            displayname="Automation Service Account",
        )

        print(f"Created API user: {user.name}")
        print(f"  Type: {user.user_type_display}")

        # Cleanup for demo
        # client.users.delete(user.key)


def create_user_with_security_options() -> None:
    """Create a user with various security options."""
    print("\n=== Create User with Security Options ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Create user with temporary password that must be changed
        user = client.users.create(
            name="newemployee",
            password="TempPass123!",
            displayname="New Employee",
            email="new@company.com",
            change_password=True,  # Force password change on first login
        )
        print(f"Created user with password change required: {user.name}")
        print(f"  Change Password: {user.change_password}")

        # Clean up
        client.users.delete(user.key)

        # Create user with 2FA enabled
        user = client.users.create(
            name="secure_user",
            password="SecurePass123!",
            email="secure@company.com",
            two_factor_enabled=True,
            two_factor_type="email",
        )
        print(f"Created user with 2FA: {user.name}")
        print(f"  2FA Enabled: {user.two_factor_enabled}")

        # Clean up
        client.users.delete(user.key)

        # Create user with physical access (admin privileges)
        user = client.users.create(
            name="sysadmin",
            password="AdminPass123!",
            displayname="System Administrator",
            email="sysadmin@company.com",
            physical_access=True,  # Grants console/SSH access
        )
        print(f"Created admin user: {user.name}")
        print(f"  Physical Access: {user.physical_access}")

        # Clean up
        client.users.delete(user.key)


def update_user() -> None:
    """Update user settings."""
    print("\n=== Update User ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Create a test user
        user = client.users.create(
            name="test_update",
            password="TestPass123!",
            email="old@example.com",
        )
        print(f"Created user: {user.name}")

        # Update display name and email
        updated = client.users.update(
            user.key,
            displayname="Updated Display Name",
            email="new@example.com",
        )
        print(f"Updated user:")
        print(f"  Display Name: {updated.displayname}")
        print(f"  Email: {updated.email}")

        # Change password
        updated = client.users.update(
            user.key,
            password="NewPassword456!",
        )
        print(f"Password changed for: {updated.name}")

        # Enable 2FA
        updated = client.users.update(
            user.key,
            two_factor_enabled=True,
            two_factor_type="email",
        )
        print(f"2FA enabled: {updated.two_factor_enabled}")

        # Clean up
        client.users.delete(user.key)


def enable_disable_users() -> None:
    """Demonstrate enabling and disabling users."""
    print("\n=== Enable/Disable Users ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Create a test user
        user = client.users.create(
            name="test_status",
            password="TestPass123!",
        )
        print(f"Created user: {user.name}, enabled={user.is_enabled}")

        # Method 1: Use manager methods
        disabled = client.users.disable(user.key)
        print(f"After disable: enabled={disabled.is_enabled}")

        enabled = client.users.enable(user.key)
        print(f"After enable: enabled={enabled.is_enabled}")

        # Method 2: Use User object methods
        user = user.disable()
        print(f"User.disable(): enabled={user.is_enabled}")

        user = user.enable()
        print(f"User.enable(): enabled={user.is_enabled}")

        # Clean up
        client.users.delete(user.key)


def filter_users_advanced() -> None:
    """Advanced user filtering examples."""
    print("\n=== Advanced Filtering ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Custom OData filter
        users = client.users.list(filter="physical_access eq true")
        print(f"Users with physical access ({len(users)}):")
        for user in users:
            print(f"  - {user.name}")

        # Filter by name
        users = client.users.list(name="admin")
        print(f"Users named 'admin' ({len(users)}):")
        for user in users:
            print(f"  - {user.name}")

        # Include system users
        all_users = client.users.list(include_system=True)
        print(f"Total users including system ({len(all_users)}):")
        for user in all_users[:5]:
            print(f"  - {user.name} ({user.user_type})")


if __name__ == "__main__":
    print("pyvergeos User Management Examples")
    print("=" * 40)
    print()
    print("NOTE: Update host/credentials in this file before running.")
    print()

    # Uncomment the examples you want to run:
    # list_users()
    # list_by_type()
    # get_user()
    # create_normal_user()
    # create_api_user()
    # create_user_with_security_options()
    # update_user()
    # enable_disable_users()
    # filter_users_advanced()

    print("See the code for examples of:")
    print("  - Listing and filtering users")
    print("  - Getting users by name or key")
    print("  - Creating normal, API, and VDI users")
    print("  - Security options (2FA, password change, physical access)")
    print("  - Updating user settings")
    print("  - Enabling and disabling users")
