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
