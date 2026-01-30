#!/usr/bin/env python3
"""Example: VM Recipe provisioning with pyvergeos.

This example demonstrates VM recipe operations including:
- Listing available recipes from the Marketplace
- Viewing recipe configuration (sections and questions)
- Deploying a VM from a recipe
- Managing recipe instances
- Working with recipe logs

VM recipes are templates for deploying virtual machines with standardized
configurations. They use a "golden image" base VM and allow customization
via questions that collect user input during deployment.

Key Concepts:
    - Repository: Collection of catalogs (e.g., "Marketplace", "Local")
    - Catalog: Container for recipes (e.g., "Operating Systems", "Applications")
    - Recipe: Template with base VM and configurable questions
    - Instance: A deployed VM linked to its source recipe
"""

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def list_recipes() -> None:
    """List available VM recipes."""
    print("=== List VM Recipes ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # List all downloaded recipes (ready to use)
        recipes = client.vm_recipes.list(downloaded=True)
        print(f"Found {len(recipes)} downloaded recipes:")

        for recipe in recipes[:10]:
            status = recipe.status_info or "Unknown"
            instances = recipe.instance_count
            print(f"  - {recipe.name}")
            print(f"    Version: {recipe.version}")
            print(f"    Status: {status}")
            print(f"    Instances: {instances}")
            print(f"    Key: {recipe.key[:16]}...")
            print()


def view_recipe_configuration() -> None:
    """View the configuration options for a recipe."""
    print("\n=== Recipe Configuration ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get a specific recipe by name
        try:
            recipe = client.vm_recipes.get(name="Ubuntu Server 22.04")
        except NotFoundError:
            # Fallback to first available recipe
            recipes = client.vm_recipes.list(downloaded=True, limit=1)
            if not recipes:
                print("No downloaded recipes available")
                return
            recipe = recipes[0]

        print(f"Recipe: {recipe.name}")
        print(f"Version: {recipe.version}")
        print(f"Description: {recipe.get('description', 'No description')}")
        print()

        # Build the recipe reference for querying questions/sections
        recipe_ref = f"vm_recipes/{recipe.key}"

        # List sections (groups of questions)
        sections = client.recipe_sections.list(recipe_ref=recipe_ref)
        print(f"Sections ({len(sections)}):")
        for section in sections:
            print(f"  - {section.name}")

        print()

        # List questions (configuration options)
        questions = client.recipe_questions.list(
            recipe_ref=recipe_ref,
            enabled=True,  # Only show enabled questions
        )
        print(f"Questions ({len(questions)}):")
        for q in questions:
            section_name = q.get("section_name", "Unknown")
            q_type = q.question_type or "unknown"
            display = q.get("display", q.name)
            default = q.get("default", "")
            required = "required" if q.is_required else "optional"

            print(f"  [{section_name}] {q.name}")
            print(f"    Type: {q_type}, {required}")
            print(f"    Display: {display}")
            if default:
                print(f"    Default: {default}")
            print()


def deploy_recipe() -> None:
    """Deploy a VM from a recipe.

    This example shows how to provision a VM using a recipe template.
    The recipe collects answers to questions and creates a customized VM.
    """
    print("\n=== Deploy VM from Recipe ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get the recipe
        try:
            recipe = client.vm_recipes.get(name="Ubuntu Server 22.04")
        except NotFoundError:
            print("Recipe 'Ubuntu Server 22.04' not found")
            return

        # First, let's see what questions need answers
        recipe_ref = f"vm_recipes/{recipe.key}"
        questions = client.recipe_questions.list(
            recipe_ref=recipe_ref,
            enabled=True,
        )

        print(f"Deploying: {recipe.name}")
        print("Required questions:")
        for q in questions:
            if q.is_required:
                print(f"  - {q.name}: {q.get('display', q.name)}")

        # Prepare answers based on common recipe question names
        # These are typical YB_* variables used by VergeOS recipes
        answers = {
            "YB_CPU_CORES": 2,
            "YB_RAM": 4096,  # 4GB in MB
            "YB_HOSTNAME": "my-ubuntu-server",
            "YB_IP_ADDR_TYPE": "dhcp",
            "YB_USER": "ubuntu",
            "YB_PASSWORD": "secure-password-here",
        }

        print(f"\nDeploying with answers: {list(answers.keys())}")

        # Deploy the recipe (creates a VM instance)
        # NOTE: Uncomment to actually deploy
        # instance = recipe.deploy(
        #     name="my-ubuntu-server",
        #     answers=answers,
        #     auto_update=False,  # Don't auto-update when recipe updates
        # )
        # print(f"Created instance: {instance.name}")
        # print(f"VM Key: {instance.vm_key}")

        print("\n(Deployment commented out - uncomment to run)")


def list_recipe_instances() -> None:
    """List VM instances created from recipes."""
    print("\n=== Recipe Instances ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # List all recipe instances
        instances = client.vm_recipe_instances.list()
        print(f"Found {len(instances)} recipe instances:")

        for inst in instances:
            recipe_name = inst.get("recipe_name", "Unknown")
            vm_name = inst.get("vm_name", inst.name)
            version = inst.get("version", "?")
            auto_update = "Yes" if inst.is_auto_update else "No"

            print(f"  - {vm_name}")
            print(f"    Recipe: {recipe_name} v{version}")
            print(f"    Auto-update: {auto_update}")
            print(f"    VM Key: {inst.vm_key}")
            print()


def recipe_scoped_operations() -> None:
    """Demonstrate scoped operations on a specific recipe.

    You can get instances and logs scoped to a specific recipe,
    making it easy to manage deployments from that recipe.
    """
    print("\n=== Recipe-Scoped Operations ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get a recipe
        recipes = client.vm_recipes.list(downloaded=True, limit=1)
        if not recipes:
            print("No recipes available")
            return

        recipe = recipes[0]
        print(f"Working with recipe: {recipe.name}")

        # Get instances for this recipe (using the scoped manager)
        instances = recipe.instances.list()
        print(f"\nInstances deployed from this recipe: {len(instances)}")
        for inst in instances:
            print(f"  - {inst.name} (VM #{inst.vm_key})")

        # Get logs for this recipe
        logs = recipe.logs.list(limit=5)
        print(f"\nRecent logs ({len(logs)}):")
        for log in logs:
            level = log.get("level", "info")
            text = log.get("text", "")[:80]
            print(f"  [{level}] {text}")

        # Check for errors
        errors = recipe.logs.list_errors(limit=3)
        if errors:
            print(f"\nRecent errors ({len(errors)}):")
            for err in errors:
                print(f"  - {err.get('text', '')[:80]}")


def download_recipe() -> None:
    """Download a recipe from the Marketplace.

    Recipes from remote repositories (like the Marketplace) must be
    downloaded before they can be used to deploy VMs.
    """
    print("\n=== Download Recipe ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Find a recipe that hasn't been downloaded yet
        not_downloaded = client.vm_recipes.list(downloaded=False, limit=5)

        if not not_downloaded:
            print("All available recipes are already downloaded")
            return

        print(f"Found {len(not_downloaded)} recipes not yet downloaded:")
        for recipe in not_downloaded:
            print(f"  - {recipe.name}")

        # Download the first one
        recipe = not_downloaded[0]
        print(f"\nDownloading: {recipe.name}...")

        # NOTE: Uncomment to actually download
        # result = recipe.download()
        # print(f"Download initiated: {result}")
        #
        # # Wait for download to complete and refresh
        # import time
        # time.sleep(5)
        # recipe = recipe.refresh()
        # print(f"Downloaded: {recipe.is_downloaded}")

        print("(Download commented out - uncomment to run)")


if __name__ == "__main__":
    print("pyvergeos VM Recipe Examples")
    print("=" * 40)
    print()
    print("NOTE: Update host/credentials in this file before running.")
    print()

    # Uncomment the examples you want to run:
    # list_recipes()
    # view_recipe_configuration()
    # deploy_recipe()
    # list_recipe_instances()
    # recipe_scoped_operations()
    # download_recipe()

    print("See the code for examples of:")
    print("  - Listing available recipes")
    print("  - Viewing recipe configuration (sections/questions)")
    print("  - Deploying a VM from a recipe")
    print("  - Managing recipe instances")
    print("  - Working with recipe logs")
    print("  - Downloading recipes from Marketplace")
