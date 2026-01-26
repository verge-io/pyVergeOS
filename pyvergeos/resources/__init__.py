"""Resource managers for VergeOS API resources."""

from pyvergeos.resources.api_keys import APIKey, APIKeyCreated, APIKeyManager
from pyvergeos.resources.base import ResourceManager, ResourceObject
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

__all__ = [
    "APIKey",
    "APIKeyCreated",
    "APIKeyManager",
    "CIFSSettings",
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
]
