#!/usr/bin/env python3
"""Example: Group and membership management with pyvergeos.

This example demonstrates group operations including:
- Listing and filtering groups
- Creating groups with various options
- Updating group settings
- Enable/disable operations
- Managing group members (users and nested groups)

Prerequisites:
- Python 3.9 or later
- pyvergeos installed
- Connected to a VergeOS system (set VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD)
- VERGE_VERIFY_SSL=false for self-signed certificates
"""

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def list_groups() -> None:
    """Demonstrate listing groups with various filters."""
    print("=" * 60)
    print("=== List Groups ===")
    print("=" * 60)

    with VergeClient.from_env() as client:
        # List all groups
        groups = client.groups.list()
        print(f"\nFound {len(groups)} groups:")

        for group in groups:
            status = "Enabled" if group.is_enabled else "Disabled"
            system = " [System]" if group.is_system_group else ""
            print(f"  - {group.name}{system}")
            print(f"    Key: {group.key}")
            print(f"    Status: {status}")
            print(f"    Description: {group.description or '(not set)'}")
            print(f"    Members: {group.member_count}")
            print()


def list_by_status() -> None:
    """List groups by enabled/disabled status."""
    print("=" * 60)
    print("=== List by Status ===")
    print("=" * 60)

    with VergeClient.from_env() as client:
        # List enabled groups
        enabled = client.groups.list_enabled()
        print(f"\nEnabled Groups ({len(enabled)}):")
        for group in enabled:
            print(f"  - {group.name}")

        # List disabled groups
        disabled = client.groups.list_disabled()
        print(f"\nDisabled Groups ({len(disabled)}):")
        for group in disabled:
            print(f"  - {group.name}")

        # List non-system groups only
        non_system = client.groups.list(include_system=False)
        print(f"\nUser Groups (non-system) ({len(non_system)}):")
        for group in non_system:
            print(f"  - {group.name}")


def get_group() -> None:
    """Get a specific group by name or key."""
    print("=" * 60)
    print("=== Get Group ===")
    print("=" * 60)

    with VergeClient.from_env() as client:
        # List groups first to get a valid key
        groups = client.groups.list(limit=1)
        if groups:
            group = groups[0]

            # Get by key
            print(f"\nGet by key ({group.key}):")
            fetched = client.groups.get(group.key)
            print(f"  Name: {fetched.name}")
            print(f"  Key: {fetched.key}")

            # Get by name
            print(f"\nGet by name ('{group.name}'):")
            fetched = client.groups.get(name=group.name)
            print(f"  Name: {fetched.name}")
            print(f"  Key: {fetched.key}")
            print(f"  Members: {fetched.member_count}")

        # Try to get a non-existent group
        print("\nGet non-existent group:")
        try:
            client.groups.get(name="this-group-does-not-exist")
        except NotFoundError as e:
            print(f"  NotFoundError raised (expected): {e}")


def create_and_manage_group() -> None:
    """Create a group, update it, and demonstrate lifecycle operations."""
    print("=" * 60)
    print("=== Create and Manage Group ===")
    print("=" * 60)

    with VergeClient.from_env() as client:
        group_name = "pyvergeos-example-group"

        # Clean up if it exists from previous run
        try:
            existing = client.groups.get(name=group_name)
            print(f"\nCleaning up existing group '{group_name}'...")
            client.groups.delete(existing.key)
        except NotFoundError:
            pass

        # Create a new group
        print(f"\nCreating group '{group_name}'...")
        group = client.groups.create(
            name=group_name,
            description="Example group created by pyvergeos",
            email="example@test.local",
        )
        print(f"  Created: {group.name} (key={group.key})")
        print(f"  Description: {group.description}")
        print(f"  Email: {group.email}")
        print(f"  Enabled: {group.is_enabled}")

        # Update the group
        print("\nUpdating group...")
        group = client.groups.update(
            group.key,
            description="Updated description via pyvergeos SDK",
        )
        print(f"  New description: {group.description}")

        # Disable the group
        print("\nDisabling group...")
        group = client.groups.disable(group.key)
        print(f"  Enabled: {group.is_enabled}")

        # Enable the group (using object method)
        print("\nEnabling group (via object method)...")
        group = group.enable()
        print(f"  Enabled: {group.is_enabled}")

        # Delete the group
        print("\nDeleting group...")
        client.groups.delete(group.key)
        print("  Deleted!")

        # Verify deletion
        try:
            client.groups.get(name=group_name)
            print("  ERROR: Group still exists!")
        except NotFoundError:
            print("  Verified: Group no longer exists")


def manage_group_members() -> None:
    """Demonstrate group member management."""
    print("=" * 60)
    print("=== Manage Group Members ===")
    print("=" * 60)

    with VergeClient.from_env() as client:
        parent_name = "pyvergeos-parent-group"
        child_name = "pyvergeos-child-group"

        # Clean up if they exist from previous run
        for name in [parent_name, child_name]:
            try:
                existing = client.groups.get(name=name)
                client.groups.delete(existing.key)
            except NotFoundError:
                pass

        # Create parent group
        print(f"\nCreating parent group '{parent_name}'...")
        parent = client.groups.create(
            name=parent_name,
            description="Parent group for member demo",
        )
        print(f"  Created: {parent.name} (key={parent.key})")

        # Create child group for nested membership demo
        print(f"\nCreating child group '{child_name}'...")
        child = client.groups.create(
            name=child_name,
            description="Child group for nesting",
        )
        print(f"  Created: {child.name} (key={child.key})")

        # List members (should be empty)
        print("\nListing members (should be empty)...")
        members = parent.members.list()
        print(f"  Members: {len(members)}")

        # Get admin user
        admin = client.users.get(name="admin")
        print(f"\nAdmin user: {admin.name} (key={admin.key})")

        # Add admin user to parent group
        print("\nAdding admin user to parent group...")
        member = parent.members.add_user(admin.key)
        print(f"  Added: {member.member_name} ({member.member_type})")
        print(f"  Membership key: {member.key}")

        # Add child group to parent group (nested membership)
        print("\nAdding child group to parent group (nested)...")
        member = parent.members.add_group(child.key)
        print(f"  Added: {member.member_name} ({member.member_type})")

        # List members
        print("\nListing members of parent group...")
        members = parent.members.list()
        print(f"  Total members: {len(members)}")
        for m in members:
            print(f"  - {m.member_name} ({m.member_type})")

        # Also demonstrate accessing members via client.groups.members()
        print("\nListing via client.groups.members()...")
        members = client.groups.members(parent.key).list()
        print(f"  Total members: {len(members)}")

        # Remove user from group
        print("\nRemoving admin user from group...")
        parent.members.remove_user(admin.key)
        print("  Removed!")

        # Remove child group from parent
        print("\nRemoving child group from parent...")
        parent.members.remove_group(child.key)
        print("  Removed!")

        # Verify removals
        members = parent.members.list()
        print(f"\nMembers after removal: {len(members)}")

        # Clean up
        print("\nCleaning up...")
        client.groups.delete(child.key)
        client.groups.delete(parent.key)
        print("  Deleted both groups!")


def member_object_operations() -> None:
    """Demonstrate operations on GroupMember objects."""
    print("=" * 60)
    print("=== GroupMember Object Operations ===")
    print("=" * 60)

    with VergeClient.from_env() as client:
        group_name = "pyvergeos-member-ops"

        # Clean up if exists
        try:
            existing = client.groups.get(name=group_name)
            client.groups.delete(existing.key)
        except NotFoundError:
            pass

        # Create group
        print(f"\nCreating group '{group_name}'...")
        group = client.groups.create(name=group_name)

        # Add admin user
        admin = client.users.get(name="admin")
        print("\nAdding admin to group...")
        member = group.members.add_user(admin.key)
        print("  Member object:")
        print(f"    key: {member.key}")
        print(f"    group_key: {member.group_key}")
        print(f"    member_type: {member.member_type}")
        print(f"    member_key: {member.member_key}")
        print(f"    member_name: {member.member_name}")
        print(f"    member_ref: {member.member_ref}")
        print(f"    creator: {member.creator}")

        # Remove via member object
        print("\nRemoving via member.remove()...")
        member.remove()
        print("  Removed!")

        # Clean up
        print("\nCleaning up...")
        client.groups.delete(group.key)
        print("  Done!")


def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 60)
    print("pyvergeos Groups Example")
    print("=" * 60)

    # Run each example
    list_groups()
    list_by_status()
    get_group()
    create_and_manage_group()
    manage_group_members()
    member_object_operations()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
