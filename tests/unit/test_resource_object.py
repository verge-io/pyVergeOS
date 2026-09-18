"""Tests for ResourceObject change tracking (issue #80)."""

from __future__ import annotations

from unittest.mock import MagicMock

from pyvergeos.resources.base import ResourceManager, ResourceObject


def _obj(**data: object) -> tuple[ResourceObject, MagicMock]:
    manager = MagicMock(spec=ResourceManager)
    return ResourceObject({"$key": 7, "name": "vm1", "enabled": False, **data}, manager), manager


class TestResourceObjectSave:
    def test_setattr_changes_are_sent(self) -> None:
        obj, manager = _obj()
        obj.cpu_cores = 4
        obj["ram"] = 2048
        obj.save()
        manager.update.assert_called_once_with(7, cpu_cores=4, ram=2048)

    def test_untouched_fields_not_sent(self) -> None:
        obj, manager = _obj()
        obj.description = "x"
        obj.save()
        assert "enabled" not in manager.update.call_args.kwargs
        assert "name" not in manager.update.call_args.kwargs

    def test_kwargs_override_dirty(self) -> None:
        obj, manager = _obj()
        obj.ram = 1024
        obj.save(ram=4096, description="d")
        manager.update.assert_called_once_with(7, ram=4096, description="d")

    def test_nothing_dirty_sends_empty(self) -> None:
        obj, manager = _obj()
        obj.save()
        manager.update.assert_called_once_with(7)

    def test_dirty_cleared_after_save(self) -> None:
        obj, manager = _obj()
        obj.ram = 1024
        obj.save()
        obj.save()
        assert manager.update.call_args_list[1].kwargs == {}

    def test_private_attrs_not_tracked(self) -> None:
        obj, manager = _obj()
        obj._cache = "internal"
        obj.save()
        manager.update.assert_called_once_with(7)
        assert "_cache" not in obj

    def test_init_data_not_dirty(self) -> None:
        obj, _ = _obj(extra=1)
        assert obj._dirty == set()


class TestSaveOverrides:
    """Subclasses overriding save() must still persist attribute assignments."""

    def test_every_override_uses_pending_changes(self) -> None:
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
                if "_pending_changes" not in inspect.getsource(cls.__dict__["save"]):
                    offenders.append(f"{module.__name__}.{cls.__name__}")
        assert offenders == []

    def test_tenant_override_sends_dirty_fields(self) -> None:
        from pyvergeos.resources.tenant_manager import Tenant, TenantManager

        manager = MagicMock(spec=TenantManager)
        tenant = Tenant({"$key": 3, "name": "t"}, manager)
        tenant.description = "x"
        tenant.save(enabled=False)
        manager.update.assert_called_once_with(3, description="x", enabled=False)
