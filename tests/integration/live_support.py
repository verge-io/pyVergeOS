"""Helpers for integration tests that talk to a live VergeOS."""

from __future__ import annotations

import os
import secrets
import time
from contextlib import suppress

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, VergeError
from pyvergeos.resources.groups import Group
from pyvergeos.resources.networks import Network


def open_live_client() -> VergeClient | None:
    """Return a client matching the ``live_client`` fixture, or None.

    ``verify_ssl`` is False, same as ``live_client``. ``VergeClient.from_env``
    defaults to verifying TLS, which fails on self-signed lab certificates.
    """
    host = os.environ.get("VERGE_HOST")
    username = os.environ.get("VERGE_USERNAME")
    password = os.environ.get("VERGE_PASSWORD")
    if not host or not username or not password:
        return None
    return VergeClient(
        host=host,
        username=username,
        password=password,
        verify_ssl=False,
    )


def create_disposable_network(client: VergeClient, *, prefix: str) -> Network:
    """Create an internal network that tests can mutate and then delete.

    Never uses the External, Core, or DMZ networks.
    """
    second = 64 + secrets.randbelow(160)
    third = secrets.randbelow(256)
    address = f"10.{second}.{third}.0/24"
    ip_address = f"10.{second}.{third}.1"
    name = f"{prefix}-{secrets.token_hex(4)}"
    return client.networks.create(
        name=name,
        network_type="internal",
        network_address=address,
        ip_address=ip_address,
        description="Disposable network for integration tests",
    )


def start_disposable_network(
    client: VergeClient, network: Network, *, timeout: float = 30
) -> Network:
    """Power on a disposable network and wait until it is running.

    ``Network.apply_rules`` is rejected with "vNet is not running" until
    power-on has finished. Returns a refreshed network object.
    """
    network.power_on()
    deadline = time.monotonic() + timeout
    while True:
        current = client.networks.get(network.key)
        if current.is_running:
            return current
        if time.monotonic() >= deadline:
            name = network.name
            raise RuntimeError(f"Network {name!r} was not running within {timeout:.0f}s")
        time.sleep(1)


def destroy_network(client: VergeClient, network: Network) -> None:
    """Power off and delete a disposable network. Swallows cleanup errors."""
    try:
        current = client.networks.get(network.key)
    except NotFoundError:
        return
    with suppress(VergeError):
        current.apply_rules()
    if current.is_running:
        with suppress(VergeError):
            current.power_off()
        time.sleep(3)
        try:
            current = client.networks.get(network.key)
        except NotFoundError:
            return
    with suppress(VergeError):
        current.delete()


def clear_group_members(group: Group) -> None:
    """Remove every member from a group. Swallows cleanup errors."""
    try:
        members = list(group.members.list())
    except VergeError:
        return
    for member in members:
        with suppress(VergeError):
            group.members.remove(member.key)


def create_reserved_membership_groups(client: VergeClient) -> tuple[Group, Group]:
    """Create a parent and child group before any test deletes a group.

    After a group is deleted, VergeOS reuses that identity for the next group
    and the recycled group cannot be a membership parent. Callers must create
    these groups before other tests delete groups, and must not delete them
    until membership tests are finished.
    """
    parent = client.groups.create(
        name=f"pytest_member_parent_{secrets.token_hex(4)}",
        description="Reserved membership parent for integration tests",
    )
    try:
        child = client.groups.create(
            name=f"pytest_member_child_{secrets.token_hex(4)}",
            description="Reserved nested group for integration tests",
        )
    except VergeError:
        with suppress(VergeError):
            client.groups.delete(parent.key)
        raise
    return parent, child


def delete_reserved_membership_groups(
    client: VergeClient, parent: Group, child: Group | None = None
) -> None:
    """Delete reserved membership groups. Swallows cleanup errors."""
    clear_group_members(parent)
    if child is not None:
        clear_group_members(child)
        with suppress(VergeError):
            client.groups.delete(child.key)
    with suppress(VergeError):
        client.groups.delete(parent.key)
