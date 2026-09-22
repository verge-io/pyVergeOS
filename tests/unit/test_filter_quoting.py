"""Regression tests for quoting at resource-manager request boundaries."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.resources.base import ResourceManager
from pyvergeos.resources.groups import GroupManager
from pyvergeos.resources.nas_cifs import NASCIFSShareManager
from pyvergeos.resources.nas_nfs import NASNFSShareManager
from pyvergeos.resources.nics import MachineNICManager
from pyvergeos.resources.site_syncs import SiteSyncIncomingManager, SiteSyncOutgoingManager
from pyvergeos.resources.vm_recipes import VmRecipeInstanceManager, VmRecipeManager


@pytest.mark.parametrize(
    "manager_type",
    [
        ResourceManager,
        GroupManager,
        NASCIFSShareManager,
        NASNFSShareManager,
        MachineNICManager,
        SiteSyncIncomingManager,
        SiteSyncOutgoingManager,
        VmRecipeManager,
    ],
)
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("O'Brien", r"name eq 'O\'Brien'"),
        (r"C:\O'Brien\share", r"name eq 'C:\\O\'Brien\\share'"),
        ("trailing\\", r"name eq 'trailing\\'"),
        ("literal*?", "name eq 'literal*?'"),
        # '{' is reserved by the literal grammar (issue #100): unescaped, a
        # balanced {...} is consumed and the lookup silently resolves to a
        # different row.
        ("br{x}ace", r"name eq 'br\{x}ace'"),
        ("{lead", r"name eq '\{lead'"),
        ("trail}", "name eq 'trail}'"),
        ("O'Brien{x}", r"name eq 'O\'Brien\{x}'"),
    ],
)
def test_get_by_name_quotes_literal(manager_type: Any, name: str, expected: str) -> None:
    client = MagicMock()
    client._request.return_value = [{"$key": 1, "name": name}]
    manager = manager_type(client)

    result = manager.get(name=name)

    assert result.name == name
    assert expected in client._request.call_args.kwargs["params"]["filter"]


@pytest.mark.parametrize(
    "manager_name", ["tasks", "task_scripts", "task_schedules", "cloudinit_files"]
)
@pytest.mark.parametrize("wildcard", [False, True])
def test_task_name_search_quotes_literal(
    mock_client: Any, wildcard: bool, manager_name: str
) -> None:
    mock_client._request = MagicMock(return_value=[])
    name = r"O'Brien\share"
    manager = getattr(mock_client, manager_name)

    manager.list(name=name + ("*" if wildcard else ""))

    # A trailing '*' is a prefix match, so it maps to bw, not a contains (#103).
    op = "bw" if wildcard else "eq"
    expected = rf"name {op} 'O\'Brien\\share'"
    assert expected in mock_client._request.call_args.kwargs["params"]["filter"]


def test_base_list_quotes_kwargs_and_preserves_raw_filter() -> None:
    client = MagicMock()
    client._request.return_value = []
    manager = ResourceManager(client)
    manager.list(name=r"O'Brien\share")
    assert client._request.call_args.kwargs["params"]["filter"] == r"name eq 'O\'Brien\\share'"

    raw = r"name eq 'already\'quoted'"
    manager.list(filter=raw)
    assert client._request.call_args.kwargs["params"]["filter"] == raw


def test_recipe_network_name_resolution_quotes_literal() -> None:
    client = MagicMock()
    client.recipe_questions.list.return_value = [{"name": "network", "type": "network"}]
    client._request.return_value = [{"$key": 42}]
    manager = VmRecipeInstanceManager(client)

    result = manager._resolve_network_answers("recipe-id", {"network": r"Internal\O'Brien"})

    assert result == {"network": 42}
    assert client._request.call_args.kwargs["params"]["filter"] == r"name eq 'Internal\\O\'Brien'"


def test_scoped_nic_lookup_keeps_parent_filter() -> None:
    client = MagicMock()
    client._request.return_value = [{"$key": 1, "name": r"O'Brien\nic"}]
    manager = MachineNICManager(client, machine_key=42)

    manager.get(name=r"O'Brien\nic")

    assert client._request.call_args.kwargs["params"]["filter"] == (
        r"machine eq 42 and (name eq 'O\'Brien\\nic')"
    )


def test_log_contains_filters_quote_windows_paths(mock_client: Any) -> None:
    mock_client._request = MagicMock(return_value=[])

    mock_client.logs.list(user=r"domain\O'Brien", text=r"C:\O'Brien\share")

    expression = mock_client._request.call_args.kwargs["params"]["filter"]
    assert r"user ct 'domain\\O\'Brien'" in expression
    assert r"text ct 'C:\\O\'Brien\\share'" in expression


def test_node_filters_quote_name_and_cluster(mock_client: Any) -> None:
    mock_client._request = MagicMock(return_value=[])

    mock_client.nodes.list(name=r"O'Brien\node", cluster=r"O'Brien\cluster")

    expression = mock_client._request.call_args.kwargs["params"]["filter"]
    assert r"name eq 'O\'Brien\\node'" in expression
    assert r"cluster#name eq 'O\'Brien\\cluster'" in expression


@pytest.mark.parametrize(
    "manager_name", ["tasks", "task_scripts", "task_schedules", "cloudinit_files"]
)
@pytest.mark.parametrize("pattern", ["*", "?", "**"])
def test_all_wildcard_name_still_sends_a_filter(
    mock_client: Any, manager_name: str, pattern: str
) -> None:
    """An all-wildcard name must not drop the filter entirely (#103 / #104).

    These managers stripped '*' and '?' from the name and appended a filter
    only ``if search_term:`` - so a name of ``"*"`` left no name condition at
    all and returned every row, the fail-open shape of #96.
    """
    mock_client._request = MagicMock(return_value=[])
    manager = getattr(mock_client, manager_name)

    manager.list(name=pattern)

    sent = mock_client._request.call_args.kwargs["params"].get("filter", "")
    assert "name " in sent, f"{manager_name} dropped the name filter for {pattern!r}"


@pytest.mark.parametrize(
    "manager_name", ["tasks", "task_scripts", "task_schedules", "cloudinit_files"]
)
def test_prefix_wildcard_is_not_a_contains(mock_client: Any, manager_name: str) -> None:
    """``name="Backup*"`` is a prefix match, not a contains match (#103 / #104)."""
    mock_client._request = MagicMock(return_value=[])
    manager = getattr(mock_client, manager_name)

    manager.list(name="Backup*")

    sent = mock_client._request.call_args.kwargs["params"]["filter"]
    assert "name bw 'Backup'" in sent
    assert " ct " not in sent
