class ClusterClientError(Exception):
    """Base exception for cluster client errors."""


class NodeOperationError(ClusterClientError):
    """Raised when an operation fails on a cluster node."""


class RollbackError(ClusterClientError):
    """Raised when rollback cannot be completed successfully."""