"""Unit tests for Network operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.networks import Network, NetworkManager


class TestNetworkManager:
    """Unit tests for NetworkManager."""

    def test_list_networks(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing networks."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "External",
                "type": "external",
                "running": True,
                "status": "running",
            },
            {
                "$key": 2,
                "name": "Internal",
                "type": "internal",
                "running": False,
                "status": "stopped",
            },
        ]

        networks = mock_client.networks.list()

        assert len(networks) == 2
        assert networks[0].name == "External"
        assert networks[1].name == "Internal"

    def test_list_networks_adds_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() includes default fields for running status."""
        mock_session.request.return_value.json.return_value = []

        mock_client.networks.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")
        # Should include running status field
        assert "running" in fields

    def test_list_internal(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing internal networks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Internal1", "type": "internal", "running": True},
        ]

        networks = mock_client.networks.list_internal()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "type eq 'internal'" in params.get("filter", "")
        assert len(networks) == 1

    def test_list_external(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing external networks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "External", "type": "external", "running": True},
        ]

        mock_client.networks.list_external()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "type eq 'external'" in params.get("filter", "")

    def test_list_running(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing running networks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Net1", "running": True, "status": "running"},
            {"$key": 2, "name": "Net2", "running": True, "status": "running"},
        ]

        networks = mock_client.networks.list_running()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "running eq true" in params.get("filter", "")
        assert len(networks) == 2

    def test_list_stopped(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing stopped networks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Net1", "running": False, "status": "stopped"},
        ]

        mock_client.networks.list_stopped()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "running eq false" in params.get("filter", "")

    def test_get_network_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a network by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 100,
            "name": "test-network",
            "type": "internal",
            "running": True,
        }

        network = mock_client.networks.get(100)

        assert network.key == 100
        assert network.name == "test-network"

    def test_get_network_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a network by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 200,
                "name": "my-network",
                "type": "internal",
            }
        ]

        network = mock_client.networks.get(name="my-network")

        assert network.name == "my-network"
        assert network.key == 200

    def test_get_network_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that NotFoundError is raised when network not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.networks.get(name="nonexistent")

    def test_create_network(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a network."""
        # First call is POST (create), second is GET (fetch full data)
        mock_session.request.return_value.json.side_effect = [
            {"$key": "300", "location": "/v4/vnets/300"},  # POST response
            {  # GET response
                "$key": 300,
                "name": "new-network",
                "type": "internal",
                "network": "10.0.0.0/24",
                "ipaddress": "10.0.0.1",
                "running": False,
            },
        ]

        network = mock_client.networks.create(
            name="new-network",
            network_type="internal",
            network_address="10.0.0.0/24",
            ip_address="10.0.0.1",
        )

        assert network.name == "new-network"
        assert network.key == 300

    def test_create_network_with_dhcp(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a network with DHCP enabled."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": "301"},
            {
                "$key": 301,
                "name": "dhcp-network",
                "dhcp_enabled": True,
                "dhcp_start": "10.0.0.100",
                "dhcp_stop": "10.0.0.200",
            },
        ]

        mock_client.networks.create(
            name="dhcp-network",
            network_address="10.0.0.0/24",
            dhcp_enabled=True,
            dhcp_start="10.0.0.100",
            dhcp_stop="10.0.0.200",
        )

        # Find the POST call
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST" and "vnets" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["dhcp_enabled"] is True
        assert body["dhcp_start"] == "10.0.0.100"
        assert body["dhcp_stop"] == "10.0.0.200"

    def test_update_network(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a network."""
        mock_session.request.return_value.json.return_value = {
            "$key": 100,
            "name": "updated-network",
            "description": "New description",
        }

        network = mock_client.networks.update(100, description="New description")

        assert network.get("description") == "New description"

    def test_delete_network(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a network."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.networks.delete(100)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "vnets/100" in call_args.kwargs["url"]


class TestNetwork:
    """Unit tests for Network object."""

    @pytest.fixture
    def network_data(self) -> dict[str, Any]:
        """Sample network data."""
        return {
            "$key": 100,
            "name": "test-network",
            "type": "internal",
            "network": "192.168.1.0/24",
            "ipaddress": "192.168.1.1",
            "running": True,
            "status": "running",
            "need_fw_apply": True,
            "need_dns_apply": False,
            "need_restart": True,
        }

    @pytest.fixture
    def mock_manager(self, mock_client: VergeClient) -> NetworkManager:
        """Create a mock network manager."""
        return mock_client.networks

    def test_network_properties(
        self, network_data: dict[str, Any], mock_manager: NetworkManager
    ) -> None:
        """Test network property accessors."""
        network = Network(network_data, mock_manager)

        assert network.key == 100
        assert network.name == "test-network"
        assert network.is_running is True
        assert network.status == "running"
        assert network.needs_rule_apply is True
        assert network.needs_dns_apply is False
        assert network.needs_restart is True

    def test_network_is_running_false(
        self, network_data: dict[str, Any], mock_manager: NetworkManager
    ) -> None:
        """Test is_running when network is stopped."""
        network_data["running"] = False
        network_data["status"] = "stopped"
        network = Network(network_data, mock_manager)

        assert network.is_running is False
        assert network.status == "stopped"

    def test_power_on(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        network_data: dict[str, Any],
    ) -> None:
        """Test powering on a network."""
        network = Network(network_data, mock_client.networks)

        network.power_on()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "poweron"
        assert body["vnet"] == 100
        assert body["params"]["apply"] is True

    def test_power_on_without_apply(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        network_data: dict[str, Any],
    ) -> None:
        """Test powering on a network without applying rules."""
        network = Network(network_data, mock_client.networks)

        network.power_on(apply_rules=False)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["params"]["apply"] is False

    def test_power_off_graceful(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        network_data: dict[str, Any],
    ) -> None:
        """Test graceful power off."""
        network = Network(network_data, mock_client.networks)

        network.power_off()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "poweroff"
        assert body["vnet"] == 100

    def test_power_off_force(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        network_data: dict[str, Any],
    ) -> None:
        """Test forced power off (killpower)."""
        network = Network(network_data, mock_client.networks)

        network.power_off(force=True)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "killpower"

    def test_restart(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        network_data: dict[str, Any],
    ) -> None:
        """Test network restart."""
        network = Network(network_data, mock_client.networks)

        network.restart()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "reset"
        assert body["params"]["apply"] is True

    def test_reset_alias(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        network_data: dict[str, Any],
    ) -> None:
        """Test that reset is an alias for restart."""
        network = Network(network_data, mock_client.networks)

        network.reset()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "reset"

    def test_apply_rules(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        network_data: dict[str, Any],
    ) -> None:
        """Test applying firewall rules."""
        network = Network(network_data, mock_client.networks)

        network.apply_rules()

        call_args = mock_session.request.call_args
        assert "vnets/100/apply" in call_args.kwargs["url"]
        assert call_args.kwargs["method"] == "PUT"

    def test_apply_dns(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        network_data: dict[str, Any],
    ) -> None:
        """Test applying DNS configuration."""
        network = Network(network_data, mock_client.networks)

        network.apply_dns()

        call_args = mock_session.request.call_args
        assert "vnets/100/applydns" in call_args.kwargs["url"]
        assert call_args.kwargs["method"] == "PUT"

    def test_chaining_power_operations(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        network_data: dict[str, Any],
    ) -> None:
        """Test that power operations return self for chaining."""
        network = Network(network_data, mock_client.networks)

        result = network.power_on()
        assert result is network

        result = network.power_off()
        assert result is network

        result = network.restart()
        assert result is network

        result = network.apply_rules()
        assert result is network

        result = network.apply_dns()
        assert result is network


class TestNetworkDiagnostics:
    """Unit tests for Network diagnostics and statistics."""

    @pytest.fixture
    def network_data(self) -> dict[str, Any]:
        """Sample network data."""
        return {
            "$key": 100,
            "name": "test-network",
            "type": "internal",
            "running": True,
            "dhcp_enabled": True,
        }

    def test_diagnostics_returns_all_by_default(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that diagnostics returns both DHCP leases and addresses by default."""
        # First call: get network, second: dhcp leases, third: addresses
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True, "dhcp_enabled": True},
            [  # DHCP leases
                {
                    "$key": 1,
                    "ip": "10.0.0.100",
                    "mac": "00:11:22:33:44:55",
                    "hostname": "client1",
                    "vendor": "Dell Inc.",
                    "expiration": 1706140800,
                },
            ],
            [  # All addresses
                {
                    "$key": 1,
                    "ip": "10.0.0.100",
                    "mac": "00:11:22:33:44:55",
                    "hostname": "client1",
                    "type": "dynamic",
                    "vendor": "Dell Inc.",
                    "description": "",
                    "expiration": 1706140800,
                },
                {
                    "$key": 2,
                    "ip": "10.0.0.1",
                    "mac": "00:00:00:00:00:01",
                    "hostname": "router",
                    "type": "static",
                    "vendor": "",
                    "description": "Router IP",
                    "expiration": 0,
                },
            ],
        ]

        diag = mock_client.networks.diagnostics(100)

        assert diag["network_key"] == 100
        assert diag["network_name"] == "test-network"
        assert diag["is_running"] is True
        assert diag["dhcp_enabled"] is True
        assert diag["dhcp_lease_count"] == 1
        assert diag["address_count"] == 2
        assert "dhcp_leases" in diag
        assert "addresses" in diag

    def test_diagnostics_dhcp_leases_only(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test diagnostics with dhcp_leases type only."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True, "dhcp_enabled": True},
            [  # DHCP leases
                {"$key": 1, "ip": "10.0.0.100", "mac": "00:11:22:33:44:55"},
            ],
        ]

        diag = mock_client.networks.diagnostics(100, diagnostic_type="dhcp_leases")

        assert "dhcp_leases" in diag
        assert "addresses" not in diag
        assert diag["dhcp_lease_count"] == 1

    def test_diagnostics_addresses_only(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test diagnostics with addresses type only."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True, "dhcp_enabled": True},
            [  # Addresses
                {"$key": 1, "ip": "10.0.0.1", "type": "static"},
                {"$key": 2, "ip": "10.0.0.2", "type": "ipalias"},
            ],
        ]

        diag = mock_client.networks.diagnostics(100, diagnostic_type="addresses")

        assert "addresses" in diag
        assert "dhcp_leases" not in diag
        assert diag["address_count"] == 2

    def test_diagnostics_address_type_mapping(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that address types are mapped to human-readable names."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True, "dhcp_enabled": True},
            [  # Addresses with various types
                {"$key": 1, "ip": "10.0.0.1", "type": "static"},
                {"$key": 2, "ip": "10.0.0.2", "type": "dynamic"},
                {"$key": 3, "ip": "10.0.0.3", "type": "ipalias"},
                {"$key": 4, "ip": "10.0.0.4", "type": "proxy"},
                {"$key": 5, "ip": "10.0.0.5", "type": "virtual"},
            ],
        ]

        diag = mock_client.networks.diagnostics(100, diagnostic_type="addresses")

        addresses = diag["addresses"]
        assert addresses[0]["type"] == "Static"
        assert addresses[0]["type_raw"] == "static"
        assert addresses[1]["type"] == "DHCP Lease"
        assert addresses[2]["type"] == "IP Alias"
        assert addresses[3]["type"] == "Proxy ARP"
        assert addresses[4]["type"] == "Virtual IP"

    def test_diagnostics_via_network_object(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        network_data: dict[str, Any],
    ) -> None:
        """Test calling diagnostics via network object."""
        network = Network(network_data, mock_client.networks)

        mock_session.request.return_value.json.side_effect = [
            network_data,  # get network
            [],  # dhcp leases
            [],  # addresses
        ]

        diag = network.diagnostics()

        assert diag["network_key"] == 100

    def test_diagnostics_empty_results(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test diagnostics with no leases or addresses."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True, "dhcp_enabled": False},
            [],  # No DHCP leases
            [],  # No addresses
        ]

        diag = mock_client.networks.diagnostics(100)

        assert diag["dhcp_lease_count"] == 0
        assert diag["address_count"] == 0
        assert diag["dhcp_leases"] == []
        assert diag["addresses"] == []

    def test_diagnostics_expiration_conversion(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that expiration timestamps are converted to datetime."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True, "dhcp_enabled": True},
            [{"$key": 1, "ip": "10.0.0.100", "expiration": 1706140800}],  # lease
            [],  # addresses
        ]

        diag = mock_client.networks.diagnostics(100)

        lease = diag["dhcp_leases"][0]
        assert lease["expiration"] is not None
        # Verify it's a datetime object
        from datetime import datetime as dt

        assert isinstance(lease["expiration"], dt)

    def test_diagnostics_expiration_zero_is_none(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that expiration of 0 is converted to None."""
        # When diagnostic_type="addresses", we skip the DHCP leases query
        # So we only need: get network, then addresses
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True, "dhcp_enabled": True},
            [{"$key": 1, "ip": "10.0.0.1", "type": "static", "expiration": 0}],
        ]

        diag = mock_client.networks.diagnostics(100, diagnostic_type="addresses")

        addr = diag["addresses"][0]
        assert addr["expiration"] is None


class TestNetworkStatistics:
    """Unit tests for Network statistics."""

    def test_statistics_returns_traffic_data(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that statistics returns traffic data."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True},  # get network
            [  # stats query
                {
                    "$key": 100,
                    "name": "test-network",
                    "tx_bps": 1024,
                    "rx_bps": 2048,
                    "tx_packets": 100,
                    "rx_packets": 200,
                    "tx_bytes": 1048576,
                    "rx_bytes": 2097152,
                }
            ],
        ]

        stats = mock_client.networks.statistics(100)

        assert stats["network_key"] == 100
        assert stats["network_name"] == "test-network"
        assert stats["is_running"] is True
        assert stats["tx_bytes_per_sec"] == 1024
        assert stats["rx_bytes_per_sec"] == 2048
        assert stats["tx_packets_per_sec"] == 100
        assert stats["rx_packets_per_sec"] == 200
        assert stats["tx_bytes_total"] == 1048576
        assert stats["rx_bytes_total"] == 2097152

    def test_statistics_formatted_bytes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that statistics includes formatted byte values."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True},
            [{"$key": 100, "tx_bytes": 1073741824, "rx_bytes": 2147483648}],  # 1GB, 2GB
        ]

        stats = mock_client.networks.statistics(100)

        assert stats["tx_total_formatted"] == "1.00 GB"
        assert stats["rx_total_formatted"] == "2.00 GB"

    def test_statistics_dmz_data(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that statistics includes DMZ interface data."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True},
            [
                {
                    "$key": 100,
                    "tx_bps": 1024,
                    "rx_bps": 2048,
                    "dmz_tx_bps": 512,
                    "dmz_rx_bps": 256,
                    "dmz_tx_bytes": 100000,
                    "dmz_rx_bytes": 200000,
                }
            ],
        ]

        stats = mock_client.networks.statistics(100)

        assert stats["dmz_tx_bytes_per_sec"] == 512
        assert stats["dmz_rx_bytes_per_sec"] == 256
        assert stats["dmz_tx_bytes_total"] == 100000
        assert stats["dmz_rx_bytes_total"] == 200000

    def test_statistics_with_history(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test statistics with historical data."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True},
            [{"$key": 100, "tx_bytes": 1000, "rx_bytes": 2000}],  # current stats
            [  # history
                {
                    "timestamp": 1706140800,
                    "sent": 100,
                    "dropped": 2,
                    "quality": 98,
                    "latency_usec_avg": 5000,
                    "latency_usec_peak": 10000,
                },
                {
                    "timestamp": 1706140700,
                    "sent": 95,
                    "dropped": 5,
                    "quality": 95,
                    "latency_usec_avg": 6000,
                    "latency_usec_peak": 12000,
                },
            ],
        ]

        stats = mock_client.networks.statistics(100, include_history=True)

        assert "history" in stats
        assert len(stats["history"]) == 2
        entry = stats["history"][0]
        assert entry["sent"] == 100
        assert entry["dropped"] == 2
        assert entry["quality"] == 98
        assert entry["latency_avg_ms"] == 5.0
        assert entry["latency_peak_ms"] == 10.0

    def test_statistics_history_limit(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test statistics history limit parameter."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True},
            [{"$key": 100}],  # current stats
            [],  # history
        ]

        mock_client.networks.statistics(100, include_history=True, history_limit=30)

        # Find the history query call
        calls = mock_session.request.call_args_list
        history_call = [
            c for c in calls if "vnet_monitor_stats_history_short" in c.kwargs.get("url", "")
        ]
        assert len(history_call) == 1
        params = history_call[0].kwargs.get("params", {})
        assert params["limit"] == "30"

    def test_statistics_via_network_object(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test calling statistics via network object."""
        network_data = {"$key": 100, "name": "test-network", "running": True}
        network = Network(network_data, mock_client.networks)

        mock_session.request.return_value.json.side_effect = [
            network_data,  # get network
            [{"$key": 100, "tx_bytes": 1000, "rx_bytes": 2000}],  # stats
        ]

        stats = network.statistics()

        assert stats["network_key"] == 100

    def test_statistics_empty_stats(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test statistics when no stats data available."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": False},
            [],  # No stats
        ]

        stats = mock_client.networks.statistics(100)

        assert stats["tx_bytes_per_sec"] is None
        assert stats["rx_bytes_per_sec"] is None
        assert stats["tx_total_formatted"] == "0 B"
        assert stats["rx_total_formatted"] == "0 B"

    def test_statistics_no_history_by_default(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that history is not included by default."""
        # Reset call count from connection validation during fixture setup
        mock_session.request.reset_mock()

        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "test-network", "running": True},
            [{"$key": 100}],  # stats
        ]

        stats = mock_client.networks.statistics(100)

        assert "history" not in stats
        # Should only have 2 calls (get network, get stats), not 3 (no history call)
        assert mock_session.request.call_count == 2
