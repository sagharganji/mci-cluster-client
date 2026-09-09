# MCI Cluster Client

A reliable Python client for creating and deleting groups across all nodes of a cluster.

The client is designed for an unstable REST API where requests may fail because of connection timeouts or 5xx server errors.

## Problem

A cluster consists of multiple nodes. Each node exposes the same REST API.

A group must be created on all nodes or deleted from all nodes.

If an operation fails on one of the nodes, previously completed changes should be rolled back so the cluster does not remain in a partially modified state.

## Assumptions

The following assumptions were made while implementing the client:

- All cluster nodes expose the same REST API.
- A create operation is successful only when the group is created on every node.
- A delete operation is successful only when the group is deleted from every node.
- Network errors, timeouts, and HTTP 5xx responses are considered transient failures and are retried.
- HTTP 4xx responses are considered permanent failures and are not retried.
- Create rollback deletes the group from nodes where it was already created.
- Delete rollback recreates the group on nodes where it was already deleted.
- Rollback itself may fail. In that case, a `RollbackError` is raised.
- Operations are executed sequentially to keep rollback behavior simple and deterministic.
- The cluster API itself is outside the scope of this project and is mocked in unit tests.

## API

The cluster exposes the following endpoints.

### Create a group

```http
POST /v1/group/
```

Request:

```json
{
  "groupId": "group-123"
}
```

Expected response:

```text
201 Created
```

### Delete a group

```http
DELETE /v1/group/
```

Request:

```json
{
  "groupId": "group-123"
}
```

Expected response:

```text
200 OK
```

### Get a group

```http
GET /v1/group/{groupId}/
```

Example successful response:

```json
{
  "groupId": "group-123"
}
```

A `404 Not Found` response means the group does not exist.

## Project Structure

```text
mci-cluster-client/
├── cluster_client/
│   ├── __init__.py
│   ├── client.py
│   └── exceptions.py
├── tests/
│   └── test_client.py
├── manifests/
├── main.py
├── requirements.txt
├── Dockerfile
├── .gitignore
└── README.md
```

## Installation

Python 3.10+ is recommended.

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```python
from cluster_client import ClusterClient

hosts = [
    "https://node1.example.com",
    "https://node2.example.com",
    "https://node3.example.com",
]

client = ClusterClient(
    hosts,
    timeout=5.0,
    max_retries=3,
)

client.create_group("group-123")
client.delete_group("group-123")
```

## Checking Cluster State

Check whether a group exists on an individual node:

```python
exists = client.group_exists(
    "https://node1.example.com",
    "group-123",
)
```

Check the state across all nodes:

```python
status = client.get_group_status("group-123")
print(status)
```

Example:

```python
{
    "https://node1.example.com": True,
    "https://node2.example.com": True,
    "https://node3.example.com": False,
}
```

Check whether the cluster is consistent:

```python
consistent = client.is_group_consistent("group-123")
```

## Retry Strategy

Requests are retried when one of the following occurs:

- Connection timeout
- Network error
- HTTP 5xx server error

HTTP 4xx responses are not retried because they are treated as permanent request errors.

The retry count and delay are configurable:

```python
client = ClusterClient(
    hosts,
    max_retries=3,
    retry_delay=0.2,
)
```

## Rollback Strategy

### Create rollback

If creation succeeds on some nodes but later fails:

```text
node1 -> created
node2 -> created
node3 -> failed
```

the client rolls back the successful changes:

```text
node2 -> delete
node1 -> delete
```

### Delete rollback

If deletion succeeds on some nodes but later fails:

```text
node1 -> deleted
node2 -> deleted
node3 -> failed
```

the client recreates the group on the nodes where deletion had already succeeded:

```text
node2 -> create
node1 -> create
```

Rollback operations are performed in reverse order.

If rollback itself fails, the client raises a `RollbackError`.

## Tests

The project uses:

- `pytest`
- `respx`
- `httpx`

Run the unit tests with:

```bash
python -m pytest -q
```

The current unit tests cover:

- Client initialization
- Successful creation on all nodes
- Create rollback
- Retry after HTTP 5xx failure
- Retry after connection timeout
- Successful deletion from all nodes
- Delete rollback
- Group existence checks
- Cluster-wide group status
- Cluster consistency detection

## Docker

Build the image:

```bash
docker build -t mci-cluster-client .
```

Run it:

```bash
docker run --rm mci-cluster-client
```

## Kubernetes

Basic Kubernetes manifests are provided in the `manifests` directory.

They demonstrate how the client could be configured and deployed in a Kubernetes environment.

## Design Notes

This implementation prioritizes correctness, reliability, and understandable rollback behavior over parallel execution.

A production implementation could additionally include:

- Structured logging
- Exponential backoff
- Jitter
- Metrics
- Distributed tracing
- Persistent operation state
- Concurrent requests
- Circuit breakers
