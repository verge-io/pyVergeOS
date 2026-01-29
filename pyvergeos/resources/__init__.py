"""Resource managers for VergeOS API resources."""

from pyvergeos.resources.api_keys import APIKey, APIKeyCreated, APIKeyManager
from pyvergeos.resources.base import ResourceManager, ResourceObject
from pyvergeos.resources.certificates import Certificate, CertificateManager
from pyvergeos.resources.cloud_snapshots import (
    CloudSnapshot,
    CloudSnapshotManager,
    CloudSnapshotTenant,
    CloudSnapshotTenantManager,
    CloudSnapshotVM,
    CloudSnapshotVMManager,
)
from pyvergeos.resources.cloudinit_files import CloudInitFile, CloudInitFileManager
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
from pyvergeos.resources.resource_groups import ResourceGroup, ResourceGroupManager
from pyvergeos.resources.shared_objects import SharedObject, SharedObjectManager
from pyvergeos.resources.site_syncs import (
    SiteSyncIncoming,
    SiteSyncIncomingManager,
    SiteSyncOutgoing,
    SiteSyncOutgoingManager,
    SiteSyncSchedule,
    SiteSyncScheduleManager,
)
from pyvergeos.resources.sites import Site, SiteManager
from pyvergeos.resources.snapshot_profiles import (
    SnapshotProfile,
    SnapshotProfileManager,
    SnapshotProfilePeriod,
    SnapshotProfilePeriodManager,
)
from pyvergeos.resources.tags import (
    Tag,
    TagCategory,
    TagCategoryManager,
    TagManager,
    TagMember,
    TagMemberManager,
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
from pyvergeos.resources.webhooks import Webhook, WebhookHistory, WebhookManager

__all__ = [
    "APIKey",
    "APIKeyCreated",
    "APIKeyManager",
    "Certificate",
    "CertificateManager",
    "CIFSSettings",
    "CloudInitFile",
    "CloudInitFileManager",
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
    "ResourceGroup",
    "ResourceGroupManager",
    "ResourceManager",
    "ResourceObject",
    "SharedObject",
    "SharedObjectManager",
    "Site",
    "SiteManager",
    "SiteSyncIncoming",
    "SiteSyncIncomingManager",
    "SiteSyncOutgoing",
    "SiteSyncOutgoingManager",
    "SiteSyncSchedule",
    "SiteSyncScheduleManager",
    "SnapshotProfile",
    "SnapshotProfileManager",
    "SnapshotProfilePeriod",
    "SnapshotProfilePeriodManager",
    "Tag",
    "TagCategory",
    "TagCategoryManager",
    "TagManager",
    "TagMember",
    "TagMemberManager",
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
    "Webhook",
    "WebhookHistory",
    "WebhookManager",
]
