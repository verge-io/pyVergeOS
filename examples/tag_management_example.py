#!/usr/bin/env python3
"""Example: Complete tag management workflow with pyvergeos.

This example demonstrates the complete tag management workflow:
1. Create tag categories (Environment, Application)
2. Create tags within categories
3. List and search tags
4. Tag resources (VMs)
5. Query tagged resources
6. Remove tag assignments
7. Cleanup created resources

At the end, all created categories, tags, and tag assignments are cleaned up.

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
    python tag_management_example.py
"""

import sys
import time

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def main() -> int:
    """Run the complete tag management workflow."""
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
    env_category_name = f"SDK-Environment-{ts}"
    app_category_name = f"SDK-Application-{ts}"
    print(f"Using unique suffix: {ts}")
    print()

    # Track created resources for cleanup
    created_categories: list[int] = []
    created_tags: list[int] = []

    try:
        # =====================================================================
        # Step 1: Create Tag Categories
        # =====================================================================
        print("=== Step 1: Create Tag Categories ===")

        # Create an Environment category (single tag selection - only one env per resource)
        env_category = client.tag_categories.create(
            name=env_category_name,
            description="Deployment environment classification",
            single_tag_selection=True,
            taggable_vms=True,
            taggable_networks=True,
            taggable_tenants=True,
        )
        created_categories.append(env_category.key)
        print(f"Created category: {env_category.name}")
        print(f"  Key: {env_category.key}")
        print(f"  Single Tag Selection: {env_category.is_single_tag_selection}")
        print(f"  Taggable Types: {env_category.get_taggable_types()}")
        print()

        # Create an Application category (multiple tags allowed)
        app_category = client.tag_categories.create(
            name=app_category_name,
            description="Application or service identification",
            single_tag_selection=False,
            taggable_vms=True,
        )
        created_categories.append(app_category.key)
        print(f"Created category: {app_category.name}")
        print(f"  Key: {app_category.key}")
        print(f"  Single Tag Selection: {app_category.is_single_tag_selection}")
        print(f"  Taggable Types: {app_category.get_taggable_types()}")
        print()

        # =====================================================================
        # Step 2: Create Tags
        # =====================================================================
        print("=== Step 2: Create Tags ===")

        # Create environment tags
        env_tags = {}
        for tag_name, description in [
            ("Production", "Production workloads"),
            ("Staging", "Pre-production testing"),
            ("Development", "Development environment"),
        ]:
            tag = client.tags.create(
                name=tag_name,
                category_key=env_category.key,
                description=description,
            )
            env_tags[tag_name] = tag
            created_tags.append(tag.key)
            print(f"Created tag: {tag.name} (key={tag.key})")

        print()

        # Create application tags
        app_tags = {}
        for tag_name, description in [
            ("WebServer", "Web server tier"),
            ("Database", "Database tier"),
            ("Cache", "Caching layer"),
        ]:
            tag = client.tags.create(
                name=tag_name,
                category_key=app_category.key,
                description=description,
            )
            app_tags[tag_name] = tag
            created_tags.append(tag.key)
            print(f"Created tag: {tag.name} (key={tag.key})")

        print()

        # =====================================================================
        # Step 3: List and Search Tags
        # =====================================================================
        print("=== Step 3: List and Search Tags ===")

        # List all tags in the Environment category
        print(f"Tags in '{env_category.name}' category:")
        env_tag_list = client.tags.list(category_key=env_category.key)
        for tag in env_tag_list:
            print(f"  - {tag.name}: {tag.description}")
        print()

        # Get a specific tag by name
        prod_tag = client.tags.get(name="Production", category_key=env_category.key)
        print(f"Found tag by name: {prod_tag.name} (key={prod_tag.key})")
        print()

        # Use the category.tags property
        print("Tags via category.tags property:")
        for tag in app_category.tags:
            print(f"  - {tag.name}")
        print()

        # =====================================================================
        # Step 4: Tag Resources (VMs)
        # =====================================================================
        print("=== Step 4: Tag Resources (VMs) ===")

        # Find a VM to tag
        vms = client.vms.list(limit=2)
        if not vms:
            print("No VMs available to tag. Skipping tagging demonstration.")
        else:
            vm = vms[0]
            print(f"Found VM to tag: {vm.name} (key={vm.key})")

            # Tag the VM with Production environment
            prod_member = client.tags.members(prod_tag.key).add_vm(vm.key)
            print("Tagged VM with: Production")
            print(f"  - Member key: {prod_member.key}")
            print(f"  - Resource type: {prod_member.resource_type_display}")
            print(f"  - Resource ref: {prod_member.resource_ref}")

            # Tag the VM with WebServer application tag
            webserver_tag = app_tags["WebServer"]
            webserver_member = client.tags.members(webserver_tag.key).add_vm(vm.key)
            print("Tagged VM with: WebServer")

            # Can also use the tag.members property
            cache_tag = app_tags["Cache"]
            cache_tag.members.add_vm(vm.key)
            print("Tagged VM with: Cache")
            print()

            # =====================================================================
            # Step 5: Query Tagged Resources
            # =====================================================================
            print("=== Step 5: Query Tagged Resources ===")

            # List all members of the Production tag
            print("Resources tagged with 'Production':")
            members = client.tags.members(prod_tag.key).list()
            for m in members:
                print(f"  - {m.resource_type_display}: key={m.resource_key}")
            print()

            # List only VMs tagged with Production
            print("VMs tagged with 'Production':")
            vm_members = client.tags.members(prod_tag.key).list(resource_type="vms")
            for m in vm_members:
                print(f"  - VM key={m.resource_key}")
            print()

            # Check what tags are assigned to the VM
            print(f"All tags assigned to VM '{vm.name}':")
            all_tags = client.tags.list()
            vm_tag_names = []
            for tag in all_tags:
                members = client.tags.members(tag.key).list(resource_type="vms")
                for m in members:
                    if m.resource_key == vm.key:
                        vm_tag_names.append(f"{tag.category_name}:{tag.name}")
            for tag_name in vm_tag_names:
                print(f"  - {tag_name}")
            print()

            # =====================================================================
            # Step 6: Remove Tag Assignments
            # =====================================================================
            print("=== Step 6: Remove Tag Assignments ===")

            # Remove Production tag from VM
            client.tags.members(prod_tag.key).remove_vm(vm.key)
            print(f"Removed 'Production' tag from VM '{vm.name}'")

            # Remove using the member object directly
            webserver_member.remove()
            print(f"Removed 'WebServer' tag from VM '{vm.name}'")

            # Remove using cache_tag.members
            cache_tag.members.remove_vm(vm.key)
            print(f"Removed 'Cache' tag from VM '{vm.name}'")
            print()

            # Verify all tag assignments are removed
            remaining_members = client.tags.members(prod_tag.key).list(resource_type="vms")
            print(f"Remaining Production tag members: {len(remaining_members)}")
            print()

        # =====================================================================
        # Step 7: Update Category and Tag
        # =====================================================================
        print("=== Step 7: Update Category and Tag ===")

        # Update category to enable additional resource types
        updated_category = client.tag_categories.update(
            env_category.key,
            taggable_nodes=True,
            taggable_clusters=True,
        )
        print(f"Updated category taggable types: {updated_category.get_taggable_types()}")

        # Update tag description
        updated_tag = client.tags.update(
            prod_tag.key,
            description="Production environment - critical workloads",
        )
        print(f"Updated tag description: {updated_tag.description}")
        print()

    except Exception as e:
        print(f"Error during workflow: {e}")
        raise
    finally:
        # =====================================================================
        # Cleanup
        # =====================================================================
        print("=== Cleanup ===")

        # Delete tags first (must delete before categories)
        for tag_key in created_tags:
            try:
                client.tags.delete(tag_key)
                print(f"Deleted tag key={tag_key}")
            except NotFoundError:
                pass  # Already deleted or doesn't exist
            except Exception as e:
                print(f"Warning: Failed to delete tag {tag_key}: {e}")

        # Delete categories
        for category_key in created_categories:
            try:
                client.tag_categories.delete(category_key)
                print(f"Deleted category key={category_key}")
            except NotFoundError:
                pass  # Already deleted or doesn't exist
            except Exception as e:
                print(f"Warning: Failed to delete category {category_key}: {e}")

        print()

    # =====================================================================
    # Summary
    # =====================================================================
    print("=== Summary ===")
    print("Tag management workflow completed successfully!")
    print()
    print("Key Concepts Demonstrated:")
    print("  1. Tag Categories - organize tags and define taggable resource types")
    print("  2. Tags - labels within categories that can be applied to resources")
    print("  3. Tag Members - assignments linking tags to resources (VMs, networks, etc.)")
    print("  4. Single Tag Selection - ensures only one tag per category per resource")
    print("  5. Tag Queries - list resources by tag for inventory and reporting")
    print()
    print("API Endpoints Used:")
    print("  - client.tag_categories.list/get/create/update/delete")
    print("  - client.tags.list/get/create/update/delete")
    print("  - client.tags.members(tag_key).list/add_vm/remove_vm")
    print("  - tag.members.list/add_vm/remove_vm  (via Tag object)")
    print()

    client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
