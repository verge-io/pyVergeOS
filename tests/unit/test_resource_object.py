"""Tests for ResourceObject change tracking (issue #80)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.resources.base import ResourceManager, ResourceObject


class PlainManager(ResourceManager[ResourceObject]):
    """Manager using the generic update(**kwargs)."""

    _endpoint = "things"


class TypedManager(ResourceManager[ResourceObject]):
    """Manager with a closed keyword-only update() signature."""

    _endpoint = "things"

    def update(self, key: int, *, description: str | None = None) -> ResourceObject:  # type: ignore[override]
        body = {} if description is None else {"description": description}
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)


def _setup(manager_cls: type[ResourceManager[Any]]) -> tuple[ResourceObject, MagicMock]:
    client = MagicMock()
    client._request.return_value = {"$key": 7, "name": "vm1", "enabled": False}
    manager = manager_cls(client)
    return ResourceObject({"$key": 7, "name": "vm1", "enabled": False}, manager), client


def _puts(client: MagicMock) -> list[dict[str, Any]]:
    return [c.kwargs["json_data"] for c in client._request.call_args_list if c.args[0] == "PUT"]


class TestPlainManagerSave:
    def test_setattr_changes_are_sent(self) -> None:
        obj, client = _setup(PlainManager)
        obj.cpu_cores = 4
        obj["ram"] = 2048
        obj.save()
        assert _puts(client) == [{"cpu_cores": 4, "ram": 2048}]

    def test_untouched_fields_not_sent(self) -> None:
        obj, client = _setup(PlainManager)
        obj.description = "x"
        obj.save()
        assert _puts(client) == [{"description": "x"}]

    def test_kwargs_override_dirty(self) -> None:
        obj, client = _setup(PlainManager)
        obj.ram = 1024
        obj.save(ram=4096, description="d")
        assert _puts(client) == [{"ram": 4096, "description": "d"}]

    def test_nothing_dirty_sends_empty(self) -> None:
        obj, client = _setup(PlainManager)
        obj.save()
        assert _puts(client) == [{}]

    def test_dirty_cleared_after_save(self) -> None:
        obj, client = _setup(PlainManager)
        obj.ram = 1024
        obj.save()
        obj.save()
        assert _puts(client) == [{"ram": 1024}, {}]

    def test_dirty_kept_when_request_fails(self) -> None:
        obj, client = _setup(PlainManager)
        client._request.side_effect = [RuntimeError("boom"), {"$key": 7}]
        obj.ram = 1024
        with pytest.raises(RuntimeError):
            obj.save()
        obj.save()
        assert _puts(client) == [{"ram": 1024}, {"ram": 1024}]

    def test_private_attrs_not_tracked(self) -> None:
        obj, client = _setup(PlainManager)
        obj._cache = "internal"
        obj.save()
        assert _puts(client) == [{}]
        assert "_cache" not in obj

    def test_init_data_not_dirty(self) -> None:
        obj, _ = _setup(PlainManager)
        assert obj._dirty == set()


class TestTypedManagerSave:
    def test_dirty_fields_bypass_typed_update(self) -> None:
        obj, client = _setup(TypedManager)
        obj.maxsize = 5  # not a parameter of TypedManager.update()
        obj.save()
        assert _puts(client) == [{"maxsize": 5}]

    def test_dirty_and_kwargs_both_sent(self) -> None:
        obj, client = _setup(TypedManager)
        obj.maxsize = 5
        obj.save(description="d")
        assert _puts(client) == [{"maxsize": 5}, {"description": "d"}]

    def test_kwargs_only_use_typed_update(self) -> None:
        obj, client = _setup(TypedManager)
        obj.save(description="d")
        assert _puts(client) == [{"description": "d"}]


class TestSaveOverrides:
    """Subclasses overriding save() must delegate to _save()."""

    def test_every_override_delegates(self) -> None:
        import importlib
        import inspect
        import pkgutil

        import pyvergeos.resources as pkg

        offenders = []
        for mod in pkgutil.iter_modules(pkg.__path__):
            module = importlib.import_module(f"pyvergeos.resources.{mod.name}")
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if not issubclass(cls, ResourceObject) or cls is ResourceObject:
                    continue
                if cls.__module__ != module.__name__ or "save" not in cls.__dict__:
                    continue
                if "self._save(" not in inspect.getsource(cls.__dict__["save"]):
                    offenders.append(f"{module.__name__}.{cls.__name__}")
        assert offenders == []

    def test_tenant_override_sends_dirty_fields(self) -> None:
        from pyvergeos.resources.tenant_manager import Tenant, TenantManager

        client = MagicMock()
        client._request.return_value = {"$key": 3, "name": "t"}
        tenant = Tenant({"$key": 3, "name": "t"}, TenantManager(client))
        tenant.description = "x"
        tenant.save()
        assert {"description": "x"} in _puts(client)


class AliasManager(ResourceManager[ResourceObject]):
    """Manager with a write-alias translation and a typed update()."""

    _endpoint = "things"

    def update(self, key: int, **kwargs: Any) -> ResourceObject:  # type: ignore[override]
        kwargs = self._prepare_write_fields(kwargs)
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        return self.get(key)

    def _prepare_write_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        if "tier" not in fields:
            return fields
        fields = dict(fields)
        fields["preferred_tier"] = str(fields.pop("tier"))
        return fields


class TestWriteAliasTranslation:
    """_save() must apply manager alias translation to dirty fields (issue #97)."""

    def test_dirty_alias_is_translated(self) -> None:
        obj, client = _setup(AliasManager)
        obj.tier = 2
        obj.save()
        assert _puts(client) == [{"preferred_tier": "2"}]

    def test_dirty_alias_and_kwargs_both_translated(self) -> None:
        obj, client = _setup(AliasManager)
        obj.tier = 2
        obj.save(name="x")
        assert _puts(client) == [{"preferred_tier": "2"}, {"name": "x"}]

    def test_api_field_passes_through(self) -> None:
        obj, client = _setup(AliasManager)
        obj.preferred_tier = "4"
        obj.save()
        assert _puts(client) == [{"preferred_tier": "4"}]

    def test_default_hook_is_identity(self) -> None:
        obj, client = _setup(PlainManager)
        obj.tier = 2
        obj.save()
        assert _puts(client) == [{"tier": 2}]


class TestRefreshInPlace:
    """refresh() must update the receiver, not just return a new object (issue #98)."""

    def _client_with_fresh(self, fresh: dict[str, Any]) -> MagicMock:
        client = MagicMock()
        client._request.return_value = fresh
        return client

    def test_refresh_mutates_receiver_and_returns_self(self) -> None:
        client = self._client_with_fresh({"$key": 7, "name": "vm1", "description": "CHANGED"})
        manager = PlainManager(client)
        obj = ResourceObject({"$key": 7, "name": "vm1", "description": "stale"}, manager)

        result = obj.refresh()

        assert result is obj
        assert obj["description"] == "CHANGED"

    def test_refresh_drops_fields_removed_on_server(self) -> None:
        client = self._client_with_fresh({"$key": 7, "name": "vm1"})
        manager = PlainManager(client)
        obj = ResourceObject({"$key": 7, "name": "vm1", "stale_field": 1}, manager)

        obj.refresh()

        assert "stale_field" not in obj

    def test_refresh_discards_unsaved_changes_and_clears_dirty(self) -> None:
        client = self._client_with_fresh({"$key": 7, "name": "server-name", "ram": 512})
        manager = PlainManager(client)
        obj = ResourceObject({"$key": 7, "name": "vm1", "ram": 512}, manager)
        obj.ram = 4096  # unsaved local change

        obj.refresh()

        assert obj["ram"] == 512
        assert obj._dirty == set()

    def test_wait_loop_observes_fresh_state(self) -> None:
        client = MagicMock()
        client._request.side_effect = [
            {"$key": 7, "running": False},
            {"$key": 7, "running": True},
        ]
        manager = PlainManager(client)
        obj = ResourceObject({"$key": 7, "running": False}, manager)

        for _ in range(5):
            obj.refresh()
            if obj["running"]:
                break
        assert obj["running"] is True
        assert client._request.call_count == 2

    def test_refresh_preserves_subclass_and_manager(self) -> None:
        from pyvergeos.resources.tenant_manager import Tenant, TenantManager

        client = MagicMock()
        client._request.return_value = {"$key": 3, "name": "t2"}
        manager = TenantManager(client)
        tenant = Tenant({"$key": 3, "name": "t1"}, manager)

        result = tenant.refresh()

        assert result is tenant
        assert isinstance(tenant, Tenant)
        assert tenant["name"] == "t2"
        assert tenant._manager is manager
