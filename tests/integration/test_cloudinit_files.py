"""Integration tests for CloudInitFile operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import time
import uuid

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def unique_name(prefix: str = "pyvergeos-test") -> str:
    """Generate a unique name for test resources."""
    return f"/{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_vm(live_client: VergeClient):
    """Get a VM to use for cloud-init file tests.

    Uses the 'test' VM if it exists, otherwise skips.
    """
    try:
        vm = live_client.vms.get(name="test")
        return vm
    except NotFoundError:
        pytest.skip("No 'test' VM available for cloud-init file tests")


@pytest.fixture
def test_cloudinit_name() -> str:
    """Generate a unique test cloud-init file name."""
    return unique_name("pyvergeos-cloudinit")


@pytest.fixture
def test_cloudinit_file(live_client: VergeClient, test_vm, test_cloudinit_name: str):
    """Create and cleanup a test cloud-init file."""
    file = live_client.cloudinit_files.create(
        vm_key=test_vm.key,
        name=test_cloudinit_name,
        contents="#cloud-config\ntest: true",
        render="No",
    )

    yield file

    # Cleanup
    try:  # noqa: SIM105
        live_client.cloudinit_files.delete(file.key)
    except NotFoundError:
        pass  # Already deleted


@pytest.mark.integration
class TestCloudInitFileListIntegration:
    """Integration tests for CloudInitFileManager list operations."""

    def test_list_cloudinit_files(self, live_client: VergeClient) -> None:
        """Test listing cloud-init files from live system."""
        files = live_client.cloudinit_files.list()

        # Should return a list (may be empty)
        assert isinstance(files, list)

        # Each file should have expected properties
        for file in files:
            assert hasattr(file, "key")
            assert hasattr(file, "name")
            assert hasattr(file, "owner")
            assert hasattr(file, "render")
            assert hasattr(file, "filesize")

    def test_list_cloudinit_files_with_limit(self, live_client: VergeClient) -> None:
        """Test listing cloud-init files with limit."""
        files = live_client.cloudinit_files.list(limit=5)

        assert isinstance(files, list)
        assert len(files) <= 5

    def test_list_cloudinit_files_for_vm(
        self, live_client: VergeClient, test_vm, test_cloudinit_file
    ) -> None:
        """Test listing cloud-init files for a specific VM."""
        files = live_client.cloudinit_files.list_for_vm(test_vm.key)

        assert isinstance(files, list)
        assert len(files) >= 1
        for file in files:
            assert file.vm_key == test_vm.key

    def test_list_cloudinit_files_with_render_filter(
        self, live_client: VergeClient
    ) -> None:
        """Test listing cloud-init files with render type filter."""
        files = live_client.cloudinit_files.list(render="No")

        assert isinstance(files, list)
        for file in files:
            assert file.render == "no"


@pytest.mark.integration
class TestCloudInitFileGetIntegration:
    """Integration tests for CloudInitFileManager get operations."""

    def test_get_cloudinit_file_by_key(
        self, live_client: VergeClient, test_cloudinit_file
    ) -> None:
        """Test getting a cloud-init file by key."""
        fetched = live_client.cloudinit_files.get(test_cloudinit_file.key)

        assert fetched.key == test_cloudinit_file.key
        assert fetched.name == test_cloudinit_file.name

    def test_get_cloudinit_file_by_name(
        self, live_client: VergeClient, test_vm, test_cloudinit_file
    ) -> None:
        """Test getting a cloud-init file by name and vm_key."""
        fetched = live_client.cloudinit_files.get(
            name=test_cloudinit_file.name,
            vm_key=test_vm.key,
        )

        assert fetched.key == test_cloudinit_file.key
        assert fetched.name == test_cloudinit_file.name

    def test_get_cloudinit_file_not_found(
        self, live_client: VergeClient, test_vm
    ) -> None:
        """Test getting a non-existent cloud-init file."""
        with pytest.raises(NotFoundError):
            live_client.cloudinit_files.get(
                name="/non-existent-file-12345",
                vm_key=test_vm.key,
            )


@pytest.mark.integration
class TestCloudInitFileCRUDIntegration:
    """Integration tests for CloudInitFile CRUD operations."""

    def test_create_and_delete_cloudinit_file(
        self, live_client: VergeClient, test_vm, test_cloudinit_name: str
    ) -> None:
        """Test creating and deleting a cloud-init file."""
        user_data = """#cloud-config
packages:
  - vim
  - curl
runcmd:
  - echo "Hello from pyvergeos integration test"
"""

        file = live_client.cloudinit_files.create(
            vm_key=test_vm.key,
            name=test_cloudinit_name,
            contents=user_data,
            render="No",
        )

        try:
            assert file.name == test_cloudinit_name
            assert file.vm_key == test_vm.key
            assert file.render == "no"
            assert file.filesize > 0

            # Verify it exists
            fetched = live_client.cloudinit_files.get(file.key)
            assert fetched.key == file.key
        finally:
            # Cleanup
            live_client.cloudinit_files.delete(file.key)

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.cloudinit_files.get(
                name=test_cloudinit_name,
                vm_key=test_vm.key,
            )

    def test_create_cloudinit_file_with_jinja2(
        self, live_client: VergeClient, test_vm, test_cloudinit_name: str
    ) -> None:
        """Test creating a cloud-init file with Jinja2 render type."""
        file = live_client.cloudinit_files.create(
            vm_key=test_vm.key,
            name=test_cloudinit_name,
            contents="#cloud-config\nhostname: {{ ds.meta_data.hostname }}",
            render="Jinja2",
        )

        try:
            assert file.render == "jinja2"
            assert file.render_display == "Jinja2"
        finally:
            live_client.cloudinit_files.delete(file.key)

    def test_create_cloudinit_file_with_variables(
        self, live_client: VergeClient, test_vm, test_cloudinit_name: str
    ) -> None:
        """Test creating a cloud-init file with Variables render type."""
        file = live_client.cloudinit_files.create(
            vm_key=test_vm.key,
            name=test_cloudinit_name,
            contents="#cloud-config\nhostname: ${vm_name}",
            render="Variables",
        )

        try:
            assert file.render == "variables"
            assert file.render_display == "Variables"
        finally:
            live_client.cloudinit_files.delete(file.key)

    def test_update_cloudinit_file_render(
        self, live_client: VergeClient, test_cloudinit_file
    ) -> None:
        """Test updating a cloud-init file render type."""
        updated = live_client.cloudinit_files.update(
            test_cloudinit_file.key,
            render="Variables",
        )

        assert updated.render == "variables"
        assert updated.render_display == "Variables"

    def test_update_cloudinit_file_contents(
        self, live_client: VergeClient, test_cloudinit_file
    ) -> None:
        """Test updating cloud-init file contents."""
        new_contents = "#cloud-config\nupdated: true\ntimestamp: " + str(int(time.time()))

        updated = live_client.cloudinit_files.update(
            test_cloudinit_file.key,
            contents=new_contents,
        )

        # Verify file size changed
        assert updated.filesize > 0

        # Verify contents via get_content
        content = updated.get_content()
        assert "updated: true" in content

    def test_update_cloudinit_file_name(
        self, live_client: VergeClient, test_vm
    ) -> None:
        """Test updating cloud-init file name."""
        original_name = unique_name("pyvergeos-original")
        new_name = unique_name("pyvergeos-renamed")

        file = live_client.cloudinit_files.create(
            vm_key=test_vm.key,
            name=original_name,
            contents="#cloud-config\ntest: rename",
            render="No",
        )

        try:
            updated = live_client.cloudinit_files.update(
                file.key,
                name=new_name,
            )

            assert updated.name == new_name

            # Verify can fetch by new name
            fetched = live_client.cloudinit_files.get(name=new_name, vm_key=test_vm.key)
            assert fetched.key == file.key
        finally:
            live_client.cloudinit_files.delete(file.key)

    def test_delete_via_object_method(
        self, live_client: VergeClient, test_vm
    ) -> None:
        """Test deleting via file object method."""
        name = unique_name("pyvergeos-delete-test")

        file = live_client.cloudinit_files.create(
            vm_key=test_vm.key,
            name=name,
            contents="#cloud-config",
            render="No",
        )

        file_key = file.key
        file.delete()

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.cloudinit_files.get(file_key)


@pytest.mark.integration
class TestCloudInitFileContentIntegration:
    """Integration tests for cloud-init file content operations."""

    def test_get_content(
        self, live_client: VergeClient, test_cloudinit_file
    ) -> None:
        """Test getting cloud-init file content."""
        content = live_client.cloudinit_files.get_content(test_cloudinit_file.key)

        assert isinstance(content, str)
        assert "#cloud-config" in content
        assert "test: true" in content

    def test_get_content_as_bytes(
        self, live_client: VergeClient, test_cloudinit_file
    ) -> None:
        """Test getting cloud-init file content as bytes."""
        content = live_client.cloudinit_files.get_content(
            test_cloudinit_file.key,
            as_bytes=True,
        )

        assert isinstance(content, bytes)
        assert b"#cloud-config" in content

    def test_get_content_via_object_method(
        self, live_client: VergeClient, test_cloudinit_file
    ) -> None:
        """Test getting content via file object method."""
        content = test_cloudinit_file.get_content()

        assert isinstance(content, str)
        assert "#cloud-config" in content

    def test_get_content_as_bytes_via_object_method(
        self, live_client: VergeClient, test_cloudinit_file
    ) -> None:
        """Test getting content as bytes via file object method."""
        content = test_cloudinit_file.get_content(as_bytes=True)

        assert isinstance(content, bytes)

    def test_roundtrip_content(
        self, live_client: VergeClient, test_vm
    ) -> None:
        """Test creating file and retrieving same content."""
        name = unique_name("pyvergeos-roundtrip")
        original_content = """#cloud-config
# Special characters test
packages:
  - vim
  - "curl >= 7.0"
write_files:
  - path: /etc/test
    content: |
      Line 1
      Line 2 with special chars: <>&"'
"""

        file = live_client.cloudinit_files.create(
            vm_key=test_vm.key,
            name=name,
            contents=original_content,
            render="No",
        )

        try:
            retrieved = file.get_content()
            assert retrieved == original_content
        finally:
            file.delete()


@pytest.mark.integration
class TestCloudInitFileObjectMethodsIntegration:
    """Integration tests for CloudInitFile object methods."""

    def test_save_via_object_method(
        self, live_client: VergeClient, test_cloudinit_file
    ) -> None:
        """Test updating via file object save method."""
        updated = test_cloudinit_file.save(render="Jinja2")

        assert updated.render == "jinja2"
        assert updated.key == test_cloudinit_file.key

    def test_vm_key_property(
        self, live_client: VergeClient, test_vm, test_cloudinit_file
    ) -> None:
        """Test vm_key property returns correct VM key."""
        assert test_cloudinit_file.vm_key == test_vm.key

    def test_modified_at_property(
        self, live_client: VergeClient, test_cloudinit_file
    ) -> None:
        """Test modified_at property returns datetime."""
        assert test_cloudinit_file.modified_at is not None
        # Verify it's a recent timestamp (within last hour)
        import datetime as dt

        now = dt.datetime.now(dt.timezone.utc)
        diff = now - test_cloudinit_file.modified_at
        assert diff.total_seconds() < 3600


@pytest.mark.integration
class TestCloudInitFileEdgeCasesIntegration:
    """Integration tests for cloud-init file edge cases."""

    def test_file_with_special_chars_in_name(
        self, live_client: VergeClient, test_vm
    ) -> None:
        """Test creating file with special characters in name."""
        name = "/pyvergeos-test_file-001"

        file = live_client.cloudinit_files.create(
            vm_key=test_vm.key,
            name=name,
            contents="#cloud-config",
            render="No",
        )

        try:
            assert file.name == name
            # Verify can fetch by name
            fetched = live_client.cloudinit_files.get(name=name, vm_key=test_vm.key)
            assert fetched.key == file.key
        finally:
            file.delete()

    def test_file_with_empty_content(
        self, live_client: VergeClient, test_vm
    ) -> None:
        """Test creating file without content."""
        name = unique_name("pyvergeos-empty")

        file = live_client.cloudinit_files.create(
            vm_key=test_vm.key,
            name=name,
            render="No",
        )

        try:
            assert file.filesize == 0
        finally:
            file.delete()

    def test_wildcard_name_search(
        self, live_client: VergeClient, test_cloudinit_file
    ) -> None:
        """Test listing with wildcard name filter."""
        # Create a file with known pattern
        files = live_client.cloudinit_files.list(name="*pyvergeos*")

        assert isinstance(files, list)
        assert len(files) >= 1
        # Verify all returned files contain 'pyvergeos'
        for file in files:
            assert "pyvergeos" in file.name
