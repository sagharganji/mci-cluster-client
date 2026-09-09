import time
from typing import Iterable

import httpx

from .exceptions import NodeOperationError, RollbackError


class ClusterClient:
    def __init__(
        self,
        hosts: Iterable[str],
        timeout: float = 5.0,
        max_retries: int = 3,
        retry_delay: float = 0.2,
    ):
        self.hosts = [host.rstrip("/") for host in hosts]
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if not self.hosts:
            raise ValueError("At least one host must be provided.")

    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = httpx.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs,
                )

                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Server error: {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                return response

            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)

        raise NodeOperationError(
            f"Request failed after {self.max_retries} attempts: {url}"
        ) from last_error

    def _delete_from_node(self, host: str, group_id: str) -> None:
        url = f"{host}/v1/group/"

        response = self._request_with_retry(
            "DELETE",
            url,
            json={"groupId": group_id},
        )

        if response.status_code != 200:
            raise NodeOperationError(
                f"Failed to delete group '{group_id}' from {host}. "
                f"Status code: {response.status_code}"
            )

    def _rollback_create(self, hosts: list[str], group_id: str) -> None:
        rollback_errors = []

        for host in reversed(hosts):
            try:
                self._delete_from_node(host, group_id)
            except NodeOperationError as exc:
                rollback_errors.append(str(exc))

        if rollback_errors:
            raise RollbackError(
                "Rollback failed on one or more nodes: "
                + "; ".join(rollback_errors)
            )

    def create_group(self, group_id: str) -> None:
        created_hosts = []

        for host in self.hosts:
            url = f"{host}/v1/group/"

            try:
                response = self._request_with_retry(
                    "POST",
                    url,
                    json={"groupId": group_id},
                )

                if response.status_code != 201:
                    raise NodeOperationError(
                        f"Failed to create group '{group_id}' on {host}. "
                        f"Status code: {response.status_code}"
                    )

                created_hosts.append(host)

            except NodeOperationError:
                if created_hosts:
                    self._rollback_create(created_hosts, group_id)

                raise

    def _create_on_node(self, host: str, group_id: str) -> None:
        url = f"{host}/v1/group/"

        response = self._request_with_retry(
            "POST",
            url,
            json={"groupId": group_id},
        )

        if response.status_code != 201:
            raise NodeOperationError(
                f"Failed to recreate group '{group_id}' on {host}. "
                f"Status code: {response.status_code}"
            )

    def _rollback_delete(self, hosts: list[str], group_id: str) -> None:
        rollback_errors = []

        for host in reversed(hosts):
            try:
                self._create_on_node(host, group_id)
            except NodeOperationError as exc:
                rollback_errors.append(str(exc))

        if rollback_errors:
            raise RollbackError(
                "Delete rollback failed on one or more nodes: "
                + "; ".join(rollback_errors)
            )

    def delete_group(self, group_id: str) -> None:
        deleted_hosts = []

        for host in self.hosts:
            try:
                self._delete_from_node(host, group_id)
                deleted_hosts.append(host)

            except NodeOperationError:
                if deleted_hosts:
                    self._rollback_delete(deleted_hosts, group_id)

                rais
    def group_exists(self, host: str, group_id: str) -> bool:
        url = f"{host}/v1/group/{group_id}/"

        response = self._request_with_retry(
            "GET",
            url,
        )

        if response.status_code == 200:
            return True

        if response.status_code == 404:
            return False

        raise NodeOperationError(
            f"Failed to check group '{group_id}' on {host}. "
            f"Status code: {response.status_code}"
        )
    def get_group_status(self, group_id: str) -> dict[str, bool]:
        status = {}

        for host in self.hosts:
            status[host] = self.group_exists(host, group_id)

        return status
    def is_group_consistent(self, group_id: str) -> bool:
        status = self.get_group_status(group_id)
        values = list(status.values())

        return all(value == values[0] for value in values)                              