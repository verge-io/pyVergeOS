"""pyvergeos - Python SDK for the VergeOS REST API v4."""

from pyvergeos.__version__ import __version__
from pyvergeos.client import VergeClient
from pyvergeos.connection import VergeConnection
from pyvergeos.constants import (
    API_VERSION,
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT,
    GB,
    KB,
    MB,
    POLL_INTERVAL,
    TASK_WAIT_TIMEOUT,
)
from pyvergeos.exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    NotConnectedError,
    NotFoundError,
    TaskError,
    TaskTimeoutError,
    ValidationError,
    VergeConnectionError,
    VergeError,
    VergeTimeoutError,
)
from pyvergeos.filters import Filter, build_filter
from pyvergeos.resources.groups import (
    Group,
    GroupManager,
    GroupMember,
    GroupMemberManager,
)
from pyvergeos.resources.tenant_nodes import TenantNode, TenantNodeManager
from pyvergeos.resources.vm_imports import (
    VmImport,
    VmImportLog,
    VmImportLogManager,
    VmImportManager,
)
from pyvergeos.resources.volume_vm_exports import (
    VolumeVmExport,
    VolumeVmExportManager,
    VolumeVmExportStat,
    VolumeVmExportStatManager,
)

__all__ = [
    # Version
    "__version__",
    # Client
    "VergeClient",
    "VergeConnection",
    # Constants
    "API_VERSION",
    "DEFAULT_PAGE_SIZE",
    "DEFAULT_TIMEOUT",
    "GB",
    "KB",
    "MB",
    "POLL_INTERVAL",
    "TASK_WAIT_TIMEOUT",
    # Exceptions
    "VergeError",
    "VergeConnectionError",
    "NotConnectedError",
    "APIError",
    "AuthenticationError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "VergeTimeoutError",
    "TaskError",
    "TaskTimeoutError",
    # Filters
    "Filter",
    "build_filter",
    # Groups
    "Group",
    "GroupManager",
    "GroupMember",
    "GroupMemberManager",
    # Tenant Nodes
    "TenantNode",
    "TenantNodeManager",
    # VM Imports
    "VmImport",
    "VmImportManager",
    "VmImportLog",
    "VmImportLogManager",
    # Volume VM Exports
    "VolumeVmExport",
    "VolumeVmExportManager",
    "VolumeVmExportStat",
    "VolumeVmExportStatManager",
]
