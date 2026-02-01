"""SDK-wide constants for pyvergeos.

This module centralizes constants used throughout the SDK to eliminate
magic numbers and improve maintainability.

Example:
    >>> from pyvergeos.constants import DEFAULT_TIMEOUT, API_VERSION
    >>> print(f"API version: {API_VERSION}")
    >>> print(f"Default timeout: {DEFAULT_TIMEOUT}s")
"""

from http import HTTPStatus

# =============================================================================
# API Configuration
# =============================================================================

#: VergeOS API version
API_VERSION = "v4"

#: API base path template (use with host)
API_BASE_PATH = f"/api/{API_VERSION}"

# =============================================================================
# Timeouts (in seconds)
# =============================================================================

#: Default timeout for HTTP requests
DEFAULT_TIMEOUT = 30

#: Timeout for task wait operations
TASK_WAIT_TIMEOUT = 300

#: Timeout for file chunk uploads
UPLOAD_CHUNK_TIMEOUT = 120

# =============================================================================
# Retry Configuration
# =============================================================================

#: Number of retry attempts for transient failures
RETRY_TOTAL = 3

#: Backoff factor for retry delay calculation (delay = backoff_factor * (2 ** retry_count))
RETRY_BACKOFF_FACTOR = 1

#: HTTP status codes that trigger automatic retry
RETRY_STATUS_CODES = frozenset(
    {
        HTTPStatus.TOO_MANY_REQUESTS,  # 429
        HTTPStatus.INTERNAL_SERVER_ERROR,  # 500
        HTTPStatus.BAD_GATEWAY,  # 502
        HTTPStatus.SERVICE_UNAVAILABLE,  # 503
        HTTPStatus.GATEWAY_TIMEOUT,  # 504
    }
)

#: HTTP methods that are safe to retry
RETRY_METHODS = frozenset({"GET", "PUT", "DELETE", "POST"})

# =============================================================================
# Polling Intervals (in seconds)
# =============================================================================

#: Default interval for task status polling
POLL_INTERVAL = 2

#: Interval for file/job status polling
POLL_INTERVAL_FAST = 0.5

# =============================================================================
# HTTP Status Code Groups
# =============================================================================

#: Success status codes
HTTP_SUCCESS_CODES = frozenset(
    {
        HTTPStatus.OK,  # 200
        HTTPStatus.CREATED,  # 201
    }
)

#: No content response (success with empty body)
HTTP_NO_CONTENT = HTTPStatus.NO_CONTENT  # 204

#: Authentication failure codes
HTTP_AUTH_FAILURE_CODES = frozenset(
    {
        HTTPStatus.UNAUTHORIZED,  # 401
        HTTPStatus.FORBIDDEN,  # 403
    }
)

#: Not found status code
HTTP_NOT_FOUND = HTTPStatus.NOT_FOUND  # 404

#: Conflict status code
HTTP_CONFLICT = HTTPStatus.CONFLICT  # 409

#: Validation error status code
HTTP_UNPROCESSABLE_ENTITY = HTTPStatus.UNPROCESSABLE_ENTITY  # 422

# =============================================================================
# HTTP Headers
# =============================================================================

#: Content-Type header for JSON requests
CONTENT_TYPE_JSON = "application/json"

#: Content-Type header for binary uploads
CONTENT_TYPE_OCTET_STREAM = "application/octet-stream"

#: Authorization header name
HEADER_AUTHORIZATION = "Authorization"

#: Content-Type header name
HEADER_CONTENT_TYPE = "Content-Type"

#: Accept header name
HEADER_ACCEPT = "Accept"

# =============================================================================
# Size Constants
# =============================================================================

#: Bytes in a kilobyte
KB = 1024

#: Bytes in a megabyte
MB = 1024 * KB

#: Bytes in a gigabyte
GB = 1024 * MB

#: Chunk size for file uploads (256 KB)
UPLOAD_CHUNK_SIZE = 256 * KB  # 262144

#: Maximum size for cloud-init file contents (64 KB)
CLOUDINIT_MAX_SIZE = 64 * KB  # 65536

# =============================================================================
# Pagination
# =============================================================================

#: Default page size for list operations
DEFAULT_PAGE_SIZE = 100

#: Maximum page size for list operations
MAX_PAGE_SIZE = 1000

# =============================================================================
# Default Values
# =============================================================================

#: Default retention period in seconds (3 days)
DEFAULT_RETENTION_SECONDS = 259200

#: Default snooze duration for alarms (24 hours in seconds)
DEFAULT_SNOOZE_DURATION = 86400

#: Default minimum snapshots to keep
DEFAULT_MIN_SNAPSHOTS = 1

# =============================================================================
# Resource Defaults
# =============================================================================

#: Default RAM for tenant nodes (16 GB in MB)
DEFAULT_TENANT_NODE_RAM_MB = 16384

#: Minimum RAM for tenant nodes (2 GB in MB)
MIN_TENANT_NODE_RAM_MB = 2048

#: Default RAM per unit in cluster config (4 GB in MB)
DEFAULT_RAM_PER_UNIT_MB = 4096

#: Maximum RAM per VM default (64 GB in MB)
DEFAULT_MAX_RAM_PER_VM_MB = 65536

#: Maximum cores per VM default
DEFAULT_MAX_CORES_PER_VM = 16
