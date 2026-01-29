"""Resource managers for VergeOS API resources."""

from pyvergeos.resources.api_keys import APIKey, APIKeyCreated, APIKeyManager
from pyvergeos.resources.base import ResourceManager, ResourceObject
from pyvergeos.resources.cloud_snapshots import (
    CloudSnapshot,
    CloudSnapshotManager,
    CloudSnapshotTenant,
    CloudSnapshotTenantManager,
    CloudSnapshotVM,
    CloudSnapshotVMManager,
)
from pyvergeos.resources.nas_cifs import NASCIFSShare, NASCIFSShareManager
from pyvergeos.resources.nas_nfs import NASNFSShare, NASNFSShareManager
from pyvergeos.resources.nas_services import (
    CIFSSettings,
    NASService,
    NASServiceManager,
    NFSSettings,
)
from pyvergeos.resources.nas_users import NASUser, NASUserManager
from pyvergeos.resources.nas_volume_browser import NASVolumeFile, NASVolumeFileManager
from pyvergeos.resources.nas_volume_syncs import NASVolumeSync, NASVolumeSyncManager
from pyvergeos.resources.nas_volumes import (
    NASVolume,
    NASVolumeManager,
    NASVolumeSnapshot,
    NASVolumeSnapshotManager,
)
from pyvergeos.resources.permissions import Permission, PermissionManager
from pyvergeos.resources.shared_objects import SharedObject, SharedObjectManager
from pyvergeos.resources.snapshot_profiles import (
    SnapshotProfile,
    SnapshotProfileManager,
    SnapshotProfilePeriod,
    SnapshotProfilePeriodManager,
)
from pyvergeos.resources.tenant_external_ips import (
    TenantExternalIP,
    TenantExternalIPManager,
)
from pyvergeos.resources.tenant_layer2 import TenantLayer2Manager, TenantLayer2Network
from pyvergeos.resources.tenant_manager import Tenant, TenantManager
from pyvergeos.resources.tenant_network_blocks import (
    TenantNetworkBlock,
    TenantNetworkBlockManager,
)
from pyvergeos.resources.tenant_snapshots import TenantSnapshot, TenantSnapshotManager
from pyvergeos.resources.tenant_storage import TenantStorage, TenantStorageManager

__all__ = [
    "APIKey",
    "APIKeyCreated",
    "APIKeyManager",
    "CIFSSettings",
    "CloudSnapshot",
    "CloudSnapshotManager",
    "CloudSnapshotTenant",
    "CloudSnapshotTenantManager",
    "CloudSnapshotVM",
    "CloudSnapshotVMManager",
    "NASCIFSShare",
    "NASCIFSShareManager",
    "NASNFSShare",
    "NASNFSShareManager",
    "NASService",
    "NASServiceManager",
    "NASUser",
    "NASUserManager",
    "NASVolume",
    "NASVolumeFile",
    "NASVolumeFileManager",
    "NASVolumeManager",
    "NASVolumeSnapshot",
    "NASVolumeSnapshotManager",
    "NASVolumeSync",
    "NASVolumeSyncManager",
    "NFSSettings",
    "Permission",
    "PermissionManager",
    "ResourceManager",
    "ResourceObject",
    "SharedObject",
    "SharedObjectManager",
    "SnapshotProfile",
    "SnapshotProfileManager",
    "SnapshotProfilePeriod",
    "SnapshotProfilePeriodManager",
    "Tenant",
    "TenantExternalIP",
    "TenantExternalIPManager",
    "TenantLayer2Manager",
    "TenantLayer2Network",
    "TenantManager",
    "TenantNetworkBlock",
    "TenantNetworkBlockManager",
    "TenantSnapshot",
    "TenantSnapshotManager",
    "TenantStorage",
    "TenantStorageManager",
]
