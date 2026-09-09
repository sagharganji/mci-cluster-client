import os

from cluster_client import ClusterClient


DEFAULT_HOSTS = [
    "https://node1.example.com",
    "https://node2.example.com",
    "https://node3.example.com",
]


def get_hosts() -> list[str]:
    raw_hosts = os.getenv("HOSTS")

    if not raw_hosts:
        return DEFAULT_HOSTS

    return [
        host.strip()
        for host in raw_hosts.split(",")
        if host.strip()
    ]


def main():
    hosts = get_hosts()

    client = ClusterClient(hosts)

    print("Configured cluster nodes:")

    for host in client.hosts:
        print(f"- {host}")


if __name__ == "__main__":
    main()