"""Helpers for integration tests that talk to a live VergeOS."""

from __future__ import annotations

import os
import secrets
import time
from contextlib import suppress
from dataclasses import dataclass

from pyvergeos import VergeClient
from pyvergeos.exceptions import APIError, NotFoundError, VergeError
from pyvergeos.resources.groups import Group
from pyvergeos.resources.networks import Network

# Core and DMZ are reserved for the platform. Tests must not mutate them.
_RESERVED_NETWORK_NAMES = frozenset({"Core", "DMZ"})


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


def create_disposable_network(
    client: VergeClient, *, prefix: str, network_type: str = "internal"
) -> Network:
    """Create a network that tests can mutate and then delete.

    Never uses the External, Core, or DMZ networks. No uplink is set, so the
    create request does not reference another network.
    """
    second = 64 + secrets.randbelow(160)
    third = secrets.randbelow(256)
    address = f"10.{second}.{third}.0/24"
    ip_address = f"10.{second}.{third}.1"
    name = f"{prefix}-{secrets.token_hex(4)}"
    if network_type == "external":
        description = "Disposable external network for integration tests"
    else:
        description = "Disposable network for integration tests"
    return client.networks.create(
        name=name,
        network_type=network_type,
        network_address=address,
        ip_address=ip_address,
        description=description,
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
    """Power off and delete a disposable network.

    Deletion is retried briefly, because a network that is still stopping
    rejects ``delete()``. A ``pytest-*`` network that is still present
    afterwards raises, so a leaked test network is not silent.
    """
    name = str(network.get("name") or "")
    try:
        current = client.networks.get(network.key)
    except NotFoundError:
        return
    with suppress(VergeError):
        current.apply_rules()

    deadline = time.monotonic() + 20
    last_error: BaseException | None = None
    while True:
        try:
            current = client.networks.get(network.key)
        except NotFoundError:
            return
        if current.is_running:
            with suppress(VergeError):
                current.power_off()
        try:
            current.delete()
        except NotFoundError:
            return
        except VergeError as exc:
            last_error = exc
        else:
            try:
                client.networks.get(network.key)
            except NotFoundError:
                return
        if time.monotonic() >= deadline:
            break
        time.sleep(2)

    if name.startswith("pytest-"):
        detail = f" ({last_error})" if last_error else ""
        raise RuntimeError(
            f"Disposable network {name!r} (key {network.key}) still exists "
            f"after delete retries{detail}"
        )


def external_mutation_allowed() -> bool:
    """True when tests may mutate the shared External network."""
    return os.environ.get("VERGE_ALLOW_EXTERNAL_MUTATION") == "1"


class DisposableExternalUnavailable(VergeError):
    """The platform did not yield an external-type disposable network."""


class ExternalNetworkUnavailable(Exception):
    """Tenant external tests cannot run without mutating a shared network."""


def create_disposable_external_network(client: VergeClient, *, prefix: str) -> Network:
    """Create an external-type network that tests can mutate and then delete.

    Does not attach an uplink. Raises ``APIError`` when the platform rejects
    the create. Raises ``DisposableExternalUnavailable`` when a network is
    created but is not external; that network is deleted first.
    """
    network = create_disposable_network(client, prefix=prefix, network_type="external")
    if str(network.get("type") or "") == "external":
        return network
    destroy_network(client, network)
    created_type = network.get("type")
    raise DisposableExternalUnavailable(
        f"Network {network.name!r} was created with type {created_type!r}, not external"
    )


def select_shared_external_network(networks: list[Network]) -> Network | None:
    """Pick a shared external network the opt-in path may mutate.

    A network named External is preferred. Core and DMZ are never selected.
    """
    named_external = next((net for net in networks if net.name == "External"), None)
    if named_external is not None:
        return named_external
    return next((net for net in networks if net.name not in _RESERVED_NETWORK_NAMES), None)


def settle_firewall_apply(client: VergeClient, network: Network, *, timeout: float = 30) -> None:
    """Apply firewall rules and require ``need_fw_apply`` to be clear."""
    deadline = time.monotonic() + timeout
    last_error: BaseException | None = None
    while True:
        current = client.networks.get(network.key)
        try:
            current.apply_rules()
        except VergeError as exc:
            last_error = exc
        else:
            last_error = None
        current = client.networks.get(network.key)
        if not current.needs_rule_apply:
            return
        if time.monotonic() >= deadline:
            detail = f" ({last_error})" if last_error else ""
            raise RuntimeError(
                f"Network {current.name!r} still has need_fw_apply after apply_rules(){detail}"
            )
        time.sleep(1)


@dataclass
class ExternalNetworkLease:
    """A network leased for tenant external tests, and how to release it."""

    network: Network
    disposable: bool

    def release(self, client: VergeClient) -> None:
        """Delete a disposable network, or apply rules on a shared one."""
        if self.disposable:
            destroy_network(client, self.network)
            return
        settle_firewall_apply(client, self.network)


def lease_tenant_external_network(client: VergeClient, *, prefix: str) -> ExternalNetworkLease:
    """Lease an external-type network for tenant block and virtual-IP tests.

    Prefers a disposable external network with no uplink. When the platform
    will not create one, a shared external network is used only if
    ``VERGE_ALLOW_EXTERNAL_MUTATION=1``. Otherwise raises
    ``ExternalNetworkUnavailable``.
    """
    created: Network | None
    try:
        created = create_disposable_external_network(client, prefix=prefix)
    except (APIError, ValueError, DisposableExternalUnavailable):
        created = None

    if created is not None:
        return ExternalNetworkLease(network=created, disposable=True)

    if not external_mutation_allowed():
        raise ExternalNetworkUnavailable(
            "No disposable external network could be created. "
            "Set VERGE_ALLOW_EXTERNAL_MUTATION=1 to run these tests against External."
        )

    chosen = select_shared_external_network(client.networks.list_external())
    if chosen is None:
        raise ExternalNetworkUnavailable("No external network available")
    return ExternalNetworkLease(network=chosen, disposable=False)


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
