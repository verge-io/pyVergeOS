"""pyvergeos - Python SDK for the VergeOS REST API v4."""

from pyvergeos.__version__ import __version__
from pyvergeos.client import VergeClient
from pyvergeos.connection import VergeConnection
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

__all__ = [
    # Version
    "__version__",
    # Client
    "VergeClient",
    "VergeConnection",
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
]
