#!/usr/bin/env python3
"""Example: Catalog and repository management with pyvergeos.

This example demonstrates catalog operations including:
- Listing catalog repositories (Local, Marketplace, Verge.io)
- Viewing repository status and configuration
- Browsing catalogs and their recipes
- Refreshing repositories to get latest recipes
- Working with repository and catalog logs

Catalogs organize recipes (VM and tenant templates) into logical groups.
Catalog repositories define where catalogs are sourced from:
- local: Locally created catalogs and recipes
- remote: Remote HTTP/HTTPS URL
- remote-git: Remote Git repository
- yottabyte: Verge.io official marketplace
- provider: Service provider catalogs (inherited from parent)

Key Concepts:
    - Repository: Source of catalogs (e.g., "Local", "Verge.io", "Marketplace")
    - Catalog: Container for recipes (e.g., "Operating Systems", "Applications")
    - Status: Repository operational state (online, refreshing, error, etc.)
"""

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def list_repositories() -> None:
    """List all catalog repositories."""
    print("=== List Catalog Repositories ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        repos = client.catalog_repositories.list()
        print(f"Found {len(repos)} repositories:")

        for repo in repos:
            print(f"\n  [{repo.key}] {repo.name}")
            print(f"      Type: {repo.repository_type}")
            print(f"      Enabled: {repo.is_enabled}")
            print(f"      Auto-refresh: {repo.get('auto_refresh', False)}")

            # Get URL for remote repositories
            if repo.is_remote:
                url = repo.get("url", "N/A")
                print(f"      URL: {url}")


def view_repository_status() -> None:
    """View status of all repositories."""
    print("\n=== Repository Status ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        repos = client.catalog_repositories.list()

        for repo in repos:
            status = repo.get_status()
            state_icon = "O" if status.is_online else ("X" if status.is_error else "?")
            print(f"\n  [{state_icon}] {repo.name}")
            print(f"      Status: {status.get('status')}")
            print(f"      State: {status.get('state')}")
            if status.is_busy:
                print("      Currently: Busy (refreshing/downloading)")
            if status.get("info"):
                print(f"      Info: {status.get('info')}")


def browse_catalogs() -> None:
    """Browse catalogs across all repositories."""
    print("\n=== Browse Catalogs ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # List all catalogs
        catalogs = client.catalogs.list()
        print(f"Found {len(catalogs)} catalogs:")

        for catalog in catalogs:
            repo_display = catalog.get("repository_display", f"Repo #{catalog.repository_key}")
            print(f"\n  {catalog.name}")
            print(f"      Repository: {repo_display}")
            print(f"      Scope: {catalog.scope}")
            print(f"      Enabled: {catalog.is_enabled}")
            print(f"      Key: {catalog.key[:20]}...")


def browse_catalogs_by_repository() -> None:
    """Browse catalogs within each repository."""
    print("\n=== Catalogs by Repository ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        repos = client.catalog_repositories.list()

        for repo in repos:
            # Use the scoped catalog manager
            catalogs = repo.catalogs.list()
            print(f"\n{repo.name} ({repo.repository_type}):")
            if catalogs:
                for cat in catalogs:
                    print(f"  - {cat.name}")
            else:
                print("  (no catalogs)")


def view_catalog_recipes() -> None:
    """View recipes in a specific catalog."""
    print("\n=== Catalog Recipes ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Try to find a catalog with recipes
        catalogs = client.catalogs.list()

        for catalog in catalogs:
            # Get VM recipes in this catalog
            recipes = client.vm_recipes.list(catalog=catalog.key, limit=10)

            if recipes:
                print(f"\nCatalog: {catalog.name}")
                print(f"VM Recipes ({len(recipes)}):")
                for recipe in recipes:
                    version = recipe.get("version", "?")
                    downloaded = "Yes" if recipe.is_downloaded else "No"
                    print(f"  - {recipe.name} v{version}")
                    print(f"      Downloaded: {downloaded}")
                break
        else:
            print("No catalogs with recipes found")


def refresh_repository() -> None:
    """Refresh a repository to fetch latest recipes.

    This triggers the repository to connect to its source and
    download any new or updated catalog/recipe information.
    """
    print("\n=== Refresh Repository ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get a remote repository
        try:
            repo = client.catalog_repositories.get(name="Verge.io")
        except NotFoundError:
            # Fallback to any remote repository
            repos = client.catalog_repositories.list()
            remote_repos = [r for r in repos if r.is_remote]
            if not remote_repos:
                print("No remote repositories found")
                return
            repo = remote_repos[0]

        print(f"Repository: {repo.name}")
        print(f"Type: {repo.repository_type}")

        # Check current status
        status = repo.get_status()
        print(f"Current status: {status.get('status')}")

        # Refresh the repository
        print("\nRefreshing repository...")
        # NOTE: Uncomment to actually refresh
        # result = repo.refresh_catalogs()
        # print(f"Refresh initiated: {result}")
        #
        # # Check status after refresh
        # import time
        # time.sleep(2)
        # status = repo.get_status()
        # print(f"New status: {status.get('status')}")

        print("(Refresh commented out - uncomment to run)")


def view_repository_logs() -> None:
    """View logs for catalog repositories."""
    print("\n=== Repository Logs ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get logs for all repositories
        logs = client.catalog_repository_logs.list(limit=10)
        print(f"Found {len(logs)} log entries:")

        for log in logs:
            level = log.get("level", "info")
            text = log.get("text", "")[:70]
            repo_display = log.get("repository_display", f"Repo #{log.repository_key}")
            print(f"  [{level}] {repo_display}: {text}")

        # Check for errors
        print("\nChecking for errors...")
        errors = client.catalog_repository_logs.list_errors(limit=5)
        if errors:
            print(f"Found {len(errors)} errors:")
            for err in errors:
                print(f"  - {err.get('text', '')[:80]}")
        else:
            print("No errors found")


def view_catalog_logs() -> None:
    """View logs for catalogs."""
    print("\n=== Catalog Logs ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get logs for all catalogs
        logs = client.catalog_logs.list(limit=10)

        if logs:
            print(f"Found {len(logs)} log entries:")
            for log in logs:
                level = log.get("level", "info")
                text = log.get("text", "")[:70]
                cat_display = log.get("catalog_display", f"Catalog #{log.catalog_key}")
                print(f"  [{level}] {cat_display}: {text}")
        else:
            print("No catalog logs found")


def scoped_log_operations() -> None:
    """View logs scoped to a specific repository or catalog."""
    print("\n=== Scoped Log Operations ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get a repository
        repos = client.catalog_repositories.list()
        if not repos:
            print("No repositories found")
            return

        repo = repos[0]
        print(f"Repository: {repo.name}")

        # Use the scoped log manager
        logs = repo.logs.list(limit=5)
        print(f"  Logs: {len(logs)} entries")
        for log in logs:
            print(f"    [{log.get('level')}] {log.get('text', '')[:50]}")

        # Get a catalog (if available)
        catalogs = client.catalogs.list(limit=1)
        if catalogs:
            catalog = catalogs[0]
            print(f"\nCatalog: {catalog.name}")

            # Use the scoped log manager
            cat_logs = catalog.logs.list(limit=5)
            print(f"  Logs: {len(cat_logs)} entries")
            for log in cat_logs:
                print(f"    [{log.get('level')}] {log.get('text', '')[:50]}")


def create_local_catalog() -> None:
    """Create a catalog in the local repository.

    Local catalogs can contain your own recipes for internal use.
    """
    print("\n=== Create Local Catalog ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get the local repository
        try:
            local_repo = client.catalog_repositories.get(name="Local")
        except NotFoundError:
            print("Local repository not found")
            return

        print(f"Local repository key: {local_repo.key}")

        # Create a new catalog
        # NOTE: Uncomment to actually create
        # catalog = client.catalogs.create(
        #     name="My Custom Recipes",
        #     repository=local_repo.key,
        #     description="Internal recipes for team use",
        #     publishing_scope="private",
        #     enabled=True,
        # )
        # print(f"Created catalog: {catalog.name}")
        # print(f"Key: {catalog.key}")

        print("(Creation commented out - uncomment to run)")


if __name__ == "__main__":
    print("pyvergeos Catalog Management Examples")
    print("=" * 40)
    print()
    print("NOTE: Update host/credentials in this file before running.")
    print()

    # Uncomment the examples you want to run:
    # list_repositories()
    # view_repository_status()
    # browse_catalogs()
    # browse_catalogs_by_repository()
    # view_catalog_recipes()
    # refresh_repository()
    # view_repository_logs()
    # view_catalog_logs()
    # scoped_log_operations()
    # create_local_catalog()

    print("See the code for examples of:")
    print("  - Listing catalog repositories")
    print("  - Viewing repository status")
    print("  - Browsing catalogs and recipes")
    print("  - Refreshing repositories")
    print("  - Working with logs")
    print("  - Creating local catalogs")
