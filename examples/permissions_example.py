#!/usr/bin/env python3
"""Example demonstrating permission management in VergeOS.

This script shows how to:
- List permissions for users and groups
- Grant permissions with different access levels
- Revoke permissions

Environment Variables:
    VERGE_HOST: VergeOS hostname or IP
    VERGE_USERNAME: Admin username
    VERGE_PASSWORD: Admin password
    VERGE_VERIFY_SSL: Set to 'false' for self-signed certs
"""

import os
import sys

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def main() -> int:
    """Run permission management examples."""
    # Create client from environment variables
    try:
        client = VergeClient.from_env()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set VERGE_HOST, VERGE_USERNAME, and VERGE_PASSWORD")
        return 1

    print(f"Connected to VergeOS {client.version}")
    print()

    try:
        # Create a test user to work with
        print("Creating test user for permission examples...")
        test_user = client.users.create(
            name="perm_example_user",
            password="ExamplePass123!",
            displayname="Permission Example User",
        )
        print(f"Created user: {test_user.name} (key={test_user.key})")
        print()

        # =====================================================================
        # List permissions for a user
        # =====================================================================
        print("=== Listing Permissions for User ===")
        user_perms = client.permissions.list(user=test_user.key)
        print(f"User {test_user.name} has {len(user_perms)} permission(s):")
        for perm in user_perms:
            access = []
            if perm.can_list:
                access.append("list")
            if perm.can_read:
                access.append("read")
            if perm.can_create:
                access.append("create")
            if perm.can_modify:
                access.append("modify")
            if perm.can_delete:
                access.append("delete")
            print(f"  - Table: {perm.table}, Access: {', '.join(access)}")
        print()

        # =====================================================================
        # Grant read-only access to VMs
        # =====================================================================
        print("=== Granting Read-Only Access to VMs ===")
        vm_perm = client.permissions.grant(
            table="vms",
            user=test_user.key,
            can_list=True,
            can_read=True,
        )
        print(f"Granted permission {vm_perm.key}:")
        print(f"  Table: {vm_perm.table}")
        print(f"  List: {vm_perm.can_list}, Read: {vm_perm.can_read}")
        print(f"  Create: {vm_perm.can_create}, Modify: {vm_perm.can_modify}")
        print(f"  Delete: {vm_perm.can_delete}")
        print(f"  Full Control: {vm_perm.has_full_control}")
        print()

        # =====================================================================
        # Grant full control on networks
        # =====================================================================
        print("=== Granting Full Control on Networks ===")
        net_perm = client.permissions.grant(
            table="vnets",
            user=test_user.key,
            full_control=True,
        )
        print(f"Granted permission {net_perm.key}:")
        print(f"  Table: {net_perm.table}")
        print(f"  Full Control: {net_perm.has_full_control}")
        print()

        # =====================================================================
        # List permissions again to see the changes
        # =====================================================================
        print("=== Updated Permissions for User ===")
        user_perms = client.permissions.list(user=test_user.key)
        print(f"User {test_user.name} now has {len(user_perms)} permission(s):")
        for perm in user_perms:
            if perm.has_full_control:
                print(f"  - Table: {perm.table}, Access: FULL CONTROL")
            else:
                access = []
                if perm.can_list:
                    access.append("list")
                if perm.can_read:
                    access.append("read")
                if perm.can_create:
                    access.append("create")
                if perm.can_modify:
                    access.append("modify")
                if perm.can_delete:
                    access.append("delete")
                print(f"  - Table: {perm.table}, Access: {', '.join(access)}")
        print()

        # =====================================================================
        # Revoke a specific permission
        # =====================================================================
        print("=== Revoking Network Permission ===")
        client.permissions.revoke(net_perm.key)
        print(f"Revoked permission {net_perm.key} (networks)")
        print()

        # =====================================================================
        # Revoke all remaining permissions for user
        # =====================================================================
        print("=== Revoking All Permissions for User ===")
        revoked_count = client.permissions.revoke_for_user(test_user.key)
        print(f"Revoked {revoked_count} permission(s)")
        print()

        # Verify permissions are gone
        final_perms = client.permissions.list(user=test_user.key)
        print(f"User {test_user.name} now has {len(final_perms)} permission(s)")
        print()

    finally:
        # Cleanup
        print("=== Cleanup ===")
        try:
            client.permissions.revoke_for_user(test_user.key)
            client.users.delete(test_user.key)
            print(f"Deleted test user: {test_user.name}")
        except (NotFoundError, NameError):
            pass
        client.disconnect()

    print()
    print("Permission examples completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
