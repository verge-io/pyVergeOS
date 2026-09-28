"""Unit tests for disposable-network helpers used by integration tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import APIError, ValidationError, VergeConnectionError, VergeError
from pyvergeos.resources.networks import Network, NetworkManager
from tests.integration import live_support
from tests.integration.live_support import (
    DisposableExternalUnavailable,
    ExternalNetworkUnavailable,
    create_disposable_external_network,
    create_disposable_network,
    external_mutation_allowed,
    lease_tenant_external_network,
    select_shared_external_network,
    settle_firewall_apply,
)


def _network(
    manager: NetworkManager,
    name: str,
    key: int = 1,
    *,
    network_type: str = "external",
    need_fw_apply: bool = False,
) -> Network:
    data: dict[str, Any] = {
        "$key": key,
        "name": name,
        "type": network_type,
        "running": False,
        "need_fw_apply": need_fw_apply,
    }
    return Network(data, manager)


def _post_body(mock_session: MagicMock) -> dict[str, Any]:
    post_calls = [
        call
        for call in mock_session.request.call_args_list
        if call.kwargs.get("method") == "POST" and "vnets" in call.kwargs.get("url", "")
    ]
    assert len(post_calls) == 1
    body = post_calls[0].kwargs.get("json", {})
    assert isinstance(body, dict)
    return body


class TestDisposableExternalNetwork:
    """Create path must not reference a shared network."""

    def test_default_disposable_network_is_internal(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": "4"},
            {"$key": 4, "name": "pytest-wg-aa", "type": "internal", "running": False},
        ]

        create_disposable_network(mock_client, prefix="pytest-wg")

        body = _post_body(mock_session)
        assert body["type"] == "internal"
        assert "interface_vnet" not in body

    def test_external_create_sets_type_and_omits_uplink(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": "11"},
            {
                "$key": 11,
                "name": "pytest-tenant-ext-ok",
                "type": "external",
                "running": False,
                "need_fw_apply": False,
            },
        ]

        network = create_disposable_external_network(mock_client, prefix="pytest-tenant-ext")

        assert network.get("type") == "external"
        body = _post_body(mock_session)
        assert body["type"] == "external"
        assert "interface_vnet" not in body
        assert body["name"].startswith("pytest-tenant-ext-")
        assert body["description"] == "Disposable external network for integration tests"

    def test_non_external_create_is_deleted(
        self, mock_client: VergeClient, mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": "9"},
            {
                "$key": 9,
                "name": "pytest-tenant-ext-dead",
                "type": "internal",
                "running": False,
            },
        ]
        destroyed: list[tuple[int, str | None]] = []

        def _destroy(client: VergeClient, network: Network) -> None:
            destroyed.append((network.key, network.get("type")))

        monkeypatch.setattr(live_support, "destroy_network", _destroy)

        with pytest.raises(DisposableExternalUnavailable, match="not external"):
            create_disposable_external_network(mock_client, prefix="pytest-tenant-ext")

        assert destroyed == [(9, "internal")]


class TestSharedExternalSelection:
    """Opt-in selection must not fall through to Core or DMZ."""

    def test_prefers_external_over_other_names(self, mock_client: VergeClient) -> None:
        manager = mock_client.networks
        chosen = select_shared_external_network(
            [
                _network(manager, "Core", 1),
                _network(manager, "Border", 2),
                _network(manager, "External", 3),
            ]
        )
        assert chosen is not None
        assert chosen.name == "External"
        assert chosen.key == 3

    def test_uses_other_external_when_external_is_absent(self, mock_client: VergeClient) -> None:
        manager = mock_client.networks
        chosen = select_shared_external_network(
            [
                _network(manager, "DMZ", 1),
                _network(manager, "Border", 4),
            ]
        )
        assert chosen is not None
        assert chosen.name == "Border"

    def test_returns_none_when_only_reserved_networks_exist(self, mock_client: VergeClient) -> None:
        manager = mock_client.networks
        chosen = select_shared_external_network(
            [
                _network(manager, "Core", 1),
                _network(manager, "DMZ", 2),
            ]
        )
        assert chosen is None


def _pending_network(name: str = "External", *, needs_rule_apply: bool = True) -> MagicMock:
    """Stand-in network. ResourceObject stores assigned methods in its dict."""
    current = MagicMock()
    current.key = 1
    current.name = name
    current.needs_rule_apply = needs_rule_apply
    return current


class TestFirewallSettle:
    """Opt-in teardown must not return while need_fw_apply is set."""

    def test_returns_after_apply_clears_flag(self) -> None:
        pending = _pending_network(needs_rule_apply=True)
        clear = _pending_network(needs_rule_apply=False)
        client = MagicMock()
        client.networks.get.side_effect = [pending, clear]

        settle_firewall_apply(client, pending, timeout=5)

        pending.apply_rules.assert_called_once()

    def test_raises_when_apply_leaves_flag_set(self) -> None:
        stuck = _pending_network(needs_rule_apply=True)
        client = MagicMock()
        client.networks.get.return_value = stuck

        with pytest.raises(RuntimeError, match="still has need_fw_apply"):
            settle_firewall_apply(client, stuck, timeout=0)

    def test_raises_when_apply_is_rejected_and_flag_stays_set(self) -> None:
        stuck = _pending_network(needs_rule_apply=True)
        stuck.apply_rules.side_effect = VergeError("vNet is not running")
        client = MagicMock()
        client.networks.get.return_value = stuck

        with pytest.raises(RuntimeError, match="vNet is not running"):
            settle_firewall_apply(client, stuck, timeout=0)


class TestTenantExternalLease:
    """Tenant tests lease a disposable network before any shared network."""

    def test_mutation_flag_requires_exact_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VERGE_ALLOW_EXTERNAL_MUTATION", raising=False)
        assert external_mutation_allowed() is False
        monkeypatch.setenv("VERGE_ALLOW_EXTERNAL_MUTATION", "true")
        assert external_mutation_allowed() is False
        monkeypatch.setenv("VERGE_ALLOW_EXTERNAL_MUTATION", "1")
        assert external_mutation_allowed() is True

    def test_disposable_lease_does_not_list_shared_networks(
        self, mock_client: VergeClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        network = _network(mock_client.networks, "pytest-tenant-ext-ab", 9)
        client = MagicMock()

        def _create(unused_client: VergeClient, *, prefix: str) -> Network:
            assert prefix == "pytest-tenant-ext"
            return network

        monkeypatch.setattr(live_support, "create_disposable_external_network", _create)

        lease = lease_tenant_external_network(client, prefix="pytest-tenant-ext")

        assert lease.disposable is True
        assert lease.network is network
        client.networks.list_external.assert_not_called()

        destroyed: list[int] = []

        def _destroy(unused_client: VergeClient, released: Network) -> None:
            destroyed.append(released.key)

        def _unexpected_apply(*args: object, **kwargs: object) -> None:
            raise AssertionError("shared apply")

        monkeypatch.setattr(live_support, "destroy_network", _destroy)
        monkeypatch.setattr(live_support, "settle_firewall_apply", _unexpected_apply)
        lease.release(client)
        assert destroyed == [9]

    def test_rejected_create_skips_unless_opt_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VERGE_ALLOW_EXTERNAL_MUTATION", raising=False)
        client = MagicMock()

        def _reject(unused_client: VergeClient, *, prefix: str) -> Network:
            raise ValidationError("external type requires an uplink")

        monkeypatch.setattr(live_support, "create_disposable_external_network", _reject)

        with pytest.raises(ExternalNetworkUnavailable, match="VERGE_ALLOW_EXTERNAL_MUTATION"):
            lease_tenant_external_network(client, prefix="pytest-tenant-ext")

        client.networks.list_external.assert_not_called()

    def test_connection_errors_are_not_a_skip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = MagicMock()

        def _down(unused_client: VergeClient, *, prefix: str) -> Network:
            raise VergeConnectionError("connection failed")

        monkeypatch.setattr(live_support, "create_disposable_external_network", _down)

        with pytest.raises(VergeConnectionError):
            lease_tenant_external_network(client, prefix="pytest-tenant-ext")

        client.networks.list_external.assert_not_called()

    def test_opt_in_uses_external_and_applies_on_release(
        self, mock_client: VergeClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VERGE_ALLOW_EXTERNAL_MUTATION", "1")
        manager = mock_client.networks
        external = _network(manager, "External", 1)
        client = MagicMock()
        client.networks.list_external.return_value = [
            _network(manager, "Core", 3),
            _network(manager, "Border", 2),
            external,
        ]

        def _reject(unused_client: VergeClient, *, prefix: str) -> Network:
            raise APIError("rejected")

        monkeypatch.setattr(live_support, "create_disposable_external_network", _reject)

        lease = lease_tenant_external_network(client, prefix="pytest-tenant-ext")

        assert lease.disposable is False
        assert lease.network.name == "External"

        applied: list[str] = []

        def _settle(unused_client: VergeClient, network: Network) -> None:
            applied.append(network.name)

        def _unexpected_delete(*args: object, **kwargs: object) -> None:
            raise AssertionError("deleted shared")

        monkeypatch.setattr(live_support, "settle_firewall_apply", _settle)
        monkeypatch.setattr(live_support, "destroy_network", _unexpected_delete)
        lease.release(client)
        assert applied == ["External"]

    def test_opt_in_refuses_core_and_dmz(
        self, mock_client: VergeClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VERGE_ALLOW_EXTERNAL_MUTATION", "1")
        manager = mock_client.networks
        client = MagicMock()
        client.networks.list_external.return_value = [
            _network(manager, "Core", 1),
            _network(manager, "DMZ", 2),
        ]

        def _reject(unused_client: VergeClient, *, prefix: str) -> Network:
            raise ValidationError("no")

        monkeypatch.setattr(live_support, "create_disposable_external_network", _reject)

        with pytest.raises(ExternalNetworkUnavailable, match="No external network"):
            lease_tenant_external_network(client, prefix="pytest-tenant-ext")


class TestTenantFixtures:
    """The two classes must not keep their own External lookup."""

    def test_classes_use_the_module_fixture(self) -> None:
        from tests.integration.test_tenants import TestTenantExternalIPs, TestTenantNetworkBlocks

        assert "external_network" not in TestTenantNetworkBlocks.__dict__
        assert "external_network" not in TestTenantExternalIPs.__dict__
