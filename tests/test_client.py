import pytest
import httpx
import respx

from cluster_client import ClusterClient


def test_client_requires_at_least_one_host():
    with pytest.raises(ValueError):
        ClusterClient([])




@respx.mock
def test_create_group_on_all_nodes():
    hosts = [
        "https://node1.example.com",
        "https://node2.example.com",
        "https://node3.example.com",
    ]

    for host in hosts:
        respx.post(f"{host}/v1/group/").mock(
            return_value=httpx.Response(201)
        )

    client = ClusterClient(hosts)

    client.create_group("group-123")


@respx.mock
def test_create_group_rolls_back_when_a_node_fails():
    hosts = [
        "https://node1.example.com",
        "https://node2.example.com",
        "https://node3.example.com",
    ]

    respx.post("https://node1.example.com/v1/group/").mock(
        return_value=httpx.Response(201)
    )

    respx.post("https://node2.example.com/v1/group/").mock(
        return_value=httpx.Response(201)
    )

    respx.post("https://node3.example.com/v1/group/").mock(
        return_value=httpx.Response(500)
    )

    delete_node1 = respx.delete(
        "https://node1.example.com/v1/group/"
    ).mock(return_value=httpx.Response(200))

    delete_node2 = respx.delete(
        "https://node2.example.com/v1/group/"
    ).mock(return_value=httpx.Response(200))

    client = ClusterClient(
        hosts,
        max_retries=1,
    )

    with pytest.raises(Exception):
        client.create_group("group-rollback-test")

    assert delete_node1.called
    assert delete_node2.called

@respx.mock
def test_create_group_retries_after_server_error():
    host = "https://node1.example.com"

    route = respx.post(f"{host}/v1/group/").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(201),
        ]
    )

    client = ClusterClient(
        [host],
        max_retries=2,
        retry_delay=0,
    )

    client.create_group("group-retry-test")

    assert route.call_count == 2
@respx.mock
def test_create_group_retries_after_timeout():
    host = "https://node1.example.com"

    route = respx.post(f"{host}/v1/group/").mock(
        side_effect=[
            httpx.ConnectTimeout("Connection timed out"),
            httpx.Response(201),
        ]
    )

    client = ClusterClient(
        [host],
        max_retries=2,
        retry_delay=0,
    )

    client.create_group("group-timeout-test")

    assert route.call_count == 2

@respx.mock
def test_delete_group_from_all_nodes():
    hosts = [
        "https://node1.example.com",
        "https://node2.example.com",
        "https://node3.example.com",
    ]

    for host in hosts:
        respx.delete(f"{host}/v1/group/").mock(
            return_value=httpx.Response(200)
        )

    client = ClusterClient(hosts)

    client.delete_group("group-delete-test")

@respx.mock
def test_delete_group_rolls_back_when_a_node_fails():
    hosts = [
        "https://node1.example.com",
        "https://node2.example.com",
        "https://node3.example.com",
    ]

    respx.delete("https://node1.example.com/v1/group/").mock(
        return_value=httpx.Response(200)
    )

    respx.delete("https://node2.example.com/v1/group/").mock(
        return_value=httpx.Response(200)
    )

    respx.delete("https://node3.example.com/v1/group/").mock(
        return_value=httpx.Response(500)
    )

    recreate_node1 = respx.post(
        "https://node1.example.com/v1/group/"
    ).mock(return_value=httpx.Response(201))

    recreate_node2 = respx.post(
        "https://node2.example.com/v1/group/"
    ).mock(return_value=httpx.Response(201))

    client = ClusterClient(
        hosts,
        max_retries=1,
    )

    with pytest.raises(Exception):
        client.delete_group("group-delete-rollback-test")

    assert recreate_node1.called
    assert recreate_node2.called

@respx.mock
def test_group_exists_returns_true_when_group_is_found():
    host = "https://node1.example.com"

    respx.get(
        f"{host}/v1/group/group-123/"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"groupId": "group-123"},
        )
    )

    client = ClusterClient([host])

    assert client.group_exists(host, "group-123") is True


@respx.mock
def test_group_exists_returns_false_when_group_is_missing():
    host = "https://node1.example.com"

    respx.get(
        f"{host}/v1/group/group-123/"
    ).mock(
        return_value=httpx.Response(404)
    )

    client = ClusterClient([host])

    assert client.group_exists(host, "group-123") is False

@respx.mock
def test_get_group_status_returns_status_for_all_nodes():
    hosts = [
        "https://node1.example.com",
        "https://node2.example.com",
        "https://node3.example.com",
    ]

    respx.get(
        "https://node1.example.com/v1/group/group-123/"
    ).mock(return_value=httpx.Response(200, json={"groupId": "group-123"}))

    respx.get(
        "https://node2.example.com/v1/group/group-123/"
    ).mock(return_value=httpx.Response(200, json={"groupId": "group-123"}))

    respx.get(
        "https://node3.example.com/v1/group/group-123/"
    ).mock(return_value=httpx.Response(404))

    client = ClusterClient(hosts)

    status = client.get_group_status("group-123")

    assert status == {
        "https://node1.example.com": True,
        "https://node2.example.com": True,
        "https://node3.example.com": False,
    }

@respx.mock
def test_is_group_consistent_returns_false_for_mixed_state():
    hosts = [
        "https://node1.example.com",
        "https://node2.example.com",
    ]

    respx.get(
        "https://node1.example.com/v1/group/group-123/"
    ).mock(return_value=httpx.Response(200, json={"groupId": "group-123"}))

    respx.get(
        "https://node2.example.com/v1/group/group-123/"
    ).mock(return_value=httpx.Response(404))

    client = ClusterClient(hosts)

    assert client.is_group_consistent("group-123") is False 

import os

from main import get_hosts


def test_get_hosts_from_environment(monkeypatch):
    monkeypatch.setenv(
        "HOSTS",
        "https://node1.example.com,https://node2.example.com",
    )

    hosts = get_hosts()

    assert hosts == [
        "https://node1.example.com",
        "https://node2.example.com",
    ]