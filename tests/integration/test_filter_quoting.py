"""Verify literal escaping against VergeOS's actual filter parser."""

import uuid

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import Filter, quote_value
from pyvergeos.resources.base import ResourceManager


@pytest.mark.integration
@pytest.mark.parametrize(
    "suffix", ["o'brien", r"back\slash", r"back\'quote", "trailing\\", 'double"quote']
)
def test_group_filter_quoting(live_client: VergeClient, suffix: str) -> None:
    name = f"sdk-quote-{uuid.uuid4().hex[:8]}-{suffix}"
    group = live_client.groups.create(name=name, enabled=False)
    try:
        assert live_client.groups.get(name=name).key == group.key
        assert [g.key for g in live_client.groups.list(name=name)] == [group.key]
        assert [g.key for g in live_client.groups.list(filter=str(Filter().eq("name", name)))] == [
            group.key
        ]
        # Exercise the inherited get implementation as well as GroupManager's override.
        manager = ResourceManager(live_client)
        manager._endpoint = "groups"
        assert manager.get(name=name).key == group.key
        assert [g.key for g in live_client.groups.list(filter=f"name ct {quote_value(name)}")] == [
            group.key
        ]
    finally:
        live_client.groups.delete(group.key)
        with pytest.raises(NotFoundError):
            live_client.groups.get(key=group.key)
