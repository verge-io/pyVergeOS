"""Resource managers for VergeOS API resources."""

from pyvergeos.resources.base import ResourceManager, ResourceObject
from pyvergeos.resources.nas import (
    CIFSSettings,
    NASService,
    NASServiceManager,
    NASVolume,
    NASVolumeManager,
    NASVolumeSnapshot,
    NASVolumeSnapshotManager,
    NFSSettings,
)

__all__ = [
    "CIFSSettings",
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
