"""Resource managers for VergeOS API resources."""

from pyvergeos.resources.base import ResourceManager, ResourceObject
from pyvergeos.resources.nas_cifs import NASCIFSShare, NASCIFSShareManager
from pyvergeos.resources.nas_nfs import NASNFSShare, NASNFSShareManager
from pyvergeos.resources.nas_services import (
    CIFSSettings,
    NASService,
    NASServiceManager,
    NFSSettings,
)
from pyvergeos.resources.nas_volumes import (
    NASVolume,
    NASVolumeManager,
    NASVolumeSnapshot,
    NASVolumeSnapshotManager,
)

__all__ = [
    "CIFSSettings",
    "NASCIFSShare",
    "NASCIFSShareManager",
    "NASNFSShare",
    "NASNFSShareManager",
    "NASService",
    "NASServiceManager",
    "NASVolume",
    "NASVolumeManager",
    "NASVolumeSnapshot",
    "NASVolumeSnapshotManager",
    "NFSSettings",
    "ResourceManager",
    "ResourceObject",
]
