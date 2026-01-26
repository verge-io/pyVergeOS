#!/usr/bin/env python3
"""Example: Complete user management workflow with pyvergeos.

This example demonstrates a complete user onboarding workflow:
1. Create a new user
2. Create a new group
3. Add user to group
4. Create an API key for the user
5. Grant permissions (everything except delete)

At the end, you'll be prompted to choose what to do with the created resources:
- Keep everything (default) - resources remain active for use
- Disable user - preserves resources but prevents login
- Delete everything - removes all created resources

Environment Variables:
    VERGE_HOST: VergeOS hostname or IP
    VERGE_USERNAME: Admin username
    VERGE_PASSWORD: Admin password
    VERGE_VERIFY_SSL: Set to 'false' for self-signed certs

Usage:
    # Set environment variables
    export VERGE_HOST=192.168.1.100
    export VERGE_USERNAME=admin
    export VERGE_PASSWORD=yourpassword
    export VERGE_VERIFY_SSL=false

    # Run the example
    python user_management_example.py
"""

import sys
import time

from pyvergeos import VergeClient


def main() -> int:
    """Run the complete user management workflow."""
    # Create client from environment variables
    try:
        client = VergeClient.from_env()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set VERGE_HOST, VERGE_USERNAME, and VERGE_PASSWORD")
        return 1

    print(f"Connected to VergeOS {client.version}")
    print()

    # Use timestamp suffix to ensure unique names
    ts = int(time.time()) % 100000
    user_name = f"pyvergeos_user_{ts}"
    group_name = f"pyvergeos_group_{ts}"
    api_key_name = f"pyvergeos_apikey_{ts}"
    print(f"Using unique suffix: {ts}")
    print()

    try:
        # =====================================================================
        # Step 1: Create a new user
        # =====================================================================
        print("=== Step 1: Create User ===")
        user = client.users.create(
            name=user_name,
            password="SecurePass123!",
            displayname="SDK Example User",
            email="example@company.local",
        )
        print(f"Created user: {user.name}")
        print(f"  Key: {user.key}")
        print(f"  Identity: {user.identity}")
        print(f"  Display Name: {user.displayname}")
        print(f"  Email: {user.email}")
        print(f"  Enabled: {user.is_enabled}")

        # Clean up any leftover permissions for this identity (identities can be reused)
        existing_perms = client.permissions.list(identity_key=user.identity)
        if existing_perms:
            print(f"  Cleaning up {len(existing_perms)} leftover permission(s)...")
            for perm in existing_perms:
                client.permissions.revoke(perm.key)
        print()

        # =====================================================================
        # Step 2: Create a new group
        # =====================================================================
        print("=== Step 2: Create Group ===")
        group = client.groups.create(
            name=group_name,
            description="SDK example group for limited admin users",
            email="group@company.local",
        )
        print(f"Created group: {group.name}")
        print(f"  Key: {group.key}")
        print(f"  Description: {group.description}")
        print(f"  Email: {group.email}")
        print(f"  Members: {group.member_count}")
        print()

        # =====================================================================
        # Step 3: Add user to group
        # =====================================================================
        print("=== Step 3: Add User to Group ===")
        membership = group.members.add_user(user.key)
        print(f"Added {user.name} to {group.name}")
        print(f"  Membership Key: {membership.key}")
        print(f"  Member Type: {membership.member_type}")

        # Verify membership
        members = group.members.list()
        print(f"  Group now has {len(members)} member(s):")
        for member in members:
            print(f"    - {member.member_name} ({member.member_type})")
        print()

        # =====================================================================
        # Step 4: Create API key for user
        # =====================================================================
        print("=== Step 4: Create API Key ===")
        api_key_result = client.api_keys.create(
            user=user.key,
            name=api_key_name,
            description="API key for SDK example automation",
            expires_in="90d",  # Expires in 90 days
        )
        print(f"Created API key: {api_key_result.name}")
        print(f"  Key ID: {api_key_result.key}")
        print()
        print("  *** IMPORTANT: Save this secret NOW! ***")
        print(f"  Secret: {api_key_result.secret}")
        print("  *** It cannot be retrieved later! ***")
        print()

        # Get the key to show expiration
        api_key = client.api_keys.get(api_key_result.key)
        print(f"  Expires: {api_key.expires_datetime}")
        print()

        # =====================================================================
        # Step 5: Grant permissions (everything except delete)
        # =====================================================================
        print("=== Step 5: Grant Permissions ===")
        print("Granting permissions (list, read, create, modify - NO delete)")
        print()

        # Grant root access "/" for access to ALL resources
        # This is the simplest way to give broad access to everything
        print("Granting root access to all resources...")
        root_perm = client.permissions.grant(
            table="/",
            user=user.key,
            can_list=True,
            can_read=True,
            can_create=True,
            can_modify=True,
            can_delete=False,  # No delete permission
        )
        print("  Granted root access '/'")
        print(f"    Permission Key: {root_perm.key}")
        print(
            f"    List: {root_perm.can_list}, Read: {root_perm.can_read}, "
            f"Create: {root_perm.can_create}, Modify: {root_perm.can_modify}, "
            f"Delete: {root_perm.can_delete}"
        )
        print()

        # =====================================================================
        # Summary: Show final state
        # =====================================================================
        print("=== Summary ===")
        print()

        # Refresh user to get latest state
        user = client.users.get(user.key)
        print(f"User: {user.name} (key={user.key})")
        print(f"  Display Name: {user.displayname}")
        print(f"  Email: {user.email}")
        print(f"  Enabled: {user.is_enabled}")
        print()

        # Show group membership
        print(f"Group: {group.name} (key={group.key})")
        members = group.members.list()
        print(f"  Members ({len(members)}):")
        for member in members:
            print(f"    - {member.member_name}")
        print()

        # Show API keys
        user_api_keys = client.api_keys.list(user=user.key)
        print(f"API Keys for {user.name} ({len(user_api_keys)}):")
        for key in user_api_keys:
            expires = key.expires_datetime or "Never"
            print(f"  - {key.name} (expires: {expires})")
        print()

        # Show permissions
        user_perms = client.permissions.list(user=user.key)
        print(f"Permissions for {user.name} ({len(user_perms)}):")
        for perm in user_perms:
            access = []
            if perm.can_list:
                access.append("L")
            if perm.can_read:
                access.append("R")
            if perm.can_create:
                access.append("C")
            if perm.can_modify:
                access.append("M")
            if perm.can_delete:
                access.append("D")
            access_str = "".join(access) if access else "None"
            print(f"  - {perm.table}: [{access_str}]")
        print()
        print("Legend: L=List, R=Read, C=Create, M=Modify, D=Delete")
        print()

        # =====================================================================
        # Test the API key (optional)
        # =====================================================================
        print("=== Testing API Key Authentication ===")
        test_client = VergeClient(
            host=client._connection.host,
            token=api_key_result.secret,
            verify_ssl=client._connection.verify_ssl,
        )
        print("Successfully connected with API key!")
        print(f"User can see {len(test_client.vms.list())} VM(s)")
        test_client.disconnect()
        print()

        # =====================================================================
        # Cleanup options
        # =====================================================================
        print("=== Cleanup Options ===")
        print("Resources created:")
        print(f"  User: {user.name} (key={user.key})")
        print(f"  Group: {group.name} (key={group.key})")
        print(f"  API Key: {api_key_result.name} (key={api_key_result.key})")
        print(f"  Permission: / (key={root_perm.key})")
        print()
        print("What would you like to do?")
        print("  1. Keep everything (default)")
        print("  2. Disable user (keeps resources but prevents login)")
        print("  3. Delete everything")
        print()

        choice = input("Enter choice [1]: ").strip() or "1"

        if choice == "2":
            print()
            print("Disabling user...")
            user = client.users.disable(user.key)
            print(f"  User {user.name} disabled (enabled={user.is_enabled})")
            print()
            print("Resources are preserved but user cannot login.")

        elif choice == "3":
            print()
            print("Deleting resources...")
            client.api_keys.delete(api_key_result.key)
            print(f"  Deleted API key: {api_key_result.name}")
            client.permissions.revoke(root_perm.key)
            print(f"  Revoked permission: {root_perm.key}")
            group.members.remove_user(user.key)
            print("  Removed user from group")
            client.users.delete(user.key)
            print(f"  Deleted user: {user.name}")
            client.groups.delete(group.key)
            print(f"  Deleted group: {group.name}")
            print()
            print("All resources deleted.")

        else:
            print()
            print("Keeping all resources.")
            print(f"  User '{user.name}' can login with password or API key.")
            print(f"  API key secret: {api_key_result.secret}")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    finally:
        client.disconnect()

    print()
    print("User management workflow completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
