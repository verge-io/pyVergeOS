"""Fixtures shared by live integration tests."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import VergeError
from pyvergeos.resources.groups import Group
from pyvergeos.resources.users import User
from tests.integration.live_support import (
    create_reserved_membership_groups,
    delete_reserved_membership_groups,
    open_live_client,
)


def _integration_groups_selected(request: pytest.FixtureRequest) -> bool:
    """True when this session collected integration group membership tests."""
    for item in request.session.items:
        path = getattr(item, "path", None)
        raw = str(path) if path is not None else str(getattr(item, "fspath", ""))
        normalized = raw.replace("\\", "/")
        if normalized.endswith("tests/integration/test_groups.py"):
            return True
    return False


@pytest.fixture(scope="module")
def live_client_module() -> Generator[VergeClient, None, None]:
    """Module-scoped client with the same TLS settings as ``live_client``."""
    client = open_live_client()
    if client is None:
        pytest.skip("Live VergeOS credentials not configured")
    yield client
    client.disconnect()


@pytest.fixture
def authenticated_user(live_client: VergeClient) -> User:
    """The user the live client authenticated as.

    Integration tests must not assume that account is named admin.
    """
    username = os.environ.get("VERGE_USERNAME")
    if not username:
        pytest.skip("VERGE_USERNAME not set")
    return live_client.users.get(name=username)


@pytest.fixture(scope="session", autouse=True)
def reserved_membership_groups(
    request: pytest.FixtureRequest,
) -> Generator[tuple[Group, Group] | None, None, None]:
    """Reserve group identities before any integration test deletes a group.

    VergeOS reuses a deleted group's identity, and that recycled group cannot
    be a membership parent. These groups are created before the first
    integration test runs and removed at session end.
    """
    if not _integration_groups_selected(request):
        yield None
        return

    client = open_live_client()
    if client is None:
        yield None
        return

    try:
        parent, child = create_reserved_membership_groups(client)
    except VergeError:
        client.disconnect()
        yield None
        return

    try:
        yield parent, child
    finally:
        delete_reserved_membership_groups(client, parent, child)
        client.disconnect()
