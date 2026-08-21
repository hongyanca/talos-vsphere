#!/usr/bin/env python3
"""Deploy or replace Talos nodes on VMware using the govc CLI."""

from __future__ import annotations

import argparse
import base64
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Sequence
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class DeploymentError(RuntimeError):
    """An error that should be shown without a Python traceback."""


def load_env_file(path: Path) -> None:
    """Load shell-style environment assignments without overriding the process."""
    if not path.is_file():
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise SystemExit(f"Error: could not read {path}: {error}") from error

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"^export\s+", line):
            line = re.sub(r"^export\s+", "", line, count=1)

        name, separator, raw_value = line.partition("=")
        name = name.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise SystemExit(f"Error: invalid assignment in {path}:{line_number}")

        try:
            values = shlex.split(raw_value, comments=True, posix=True)
        except ValueError as error:
            raise SystemExit(f"Error: invalid quoted value in {path}:{line_number}") from error
        if len(values) > 1:
            raise SystemExit(f"Error: unquoted whitespace in value at {path}:{line_number}")

        os.environ.setdefault(name, values[0] if values else "")


ENV_FILE = Path(__file__).resolve().parent / ".env"
load_env_file(ENV_FILE)


CLUSTER_NAME = os.environ.get("CLUSTER_NAME") or "k8s"
TALOS_LATEST_RELEASE_URL = "https://api.github.com/repos/siderolabs/talos/releases/latest"
TALOS_RELEASE_BY_TAG_URL = "https://api.github.com/repos/siderolabs/talos/releases/tags/{version}"
TALOS_FACTORY_SCHEMATIC = "80966aaec211a8562cd422cdfb2fb67644db9f135e5bf5f26017eefe71391b67"
KUBERNETES_IMAGE_PATTERN = re.compile(
    r"(?P<image>"
    r"registry\.k8s\.io/(?:kube-apiserver|kube-controller-manager|kube-scheduler|kube-proxy)"
    r"|ghcr\.io/siderolabs/kubelet"
    r"):(?P<version>v\d+\.\d+\.\d+)"
)

CONTROL_PLANE_CPU = os.environ.get("CONTROL_PLANE_CPU") or "4"
CONTROL_PLANE_MEM = os.environ.get("CONTROL_PLANE_MEM") or "8192"
CONTROL_PLANE_DISK = os.environ.get("CONTROL_PLANE_DISK") or "15G"
CONTROL_PLANE_MACHINE_CONFIG_PATHS = (
    Path("./controlplane-1.yaml"),
    Path("./controlplane-2.yaml"),
    Path("./controlplane-3.yaml"),
)

WORKER_CPU = os.environ.get("WORKER_CPU") or "4"
WORKER_MEM = os.environ.get("WORKER_MEM") or "8192"
WORKER_DISK = os.environ.get("WORKER_DISK") or "30G"
WORKER_MACHINE_CONFIG_PATHS = (
    Path("./worker-1.yaml"),
    Path("./worker-2.yaml"),
    Path("./worker-3.yaml"),
)


def github_headers() -> dict[str, str]:
    """Return headers for GitHub API requests."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "talos-vsphere-vmware-deploy-node",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    return headers


@lru_cache(maxsize=None)
def fetch_release(url: str) -> dict[str, object]:
    """Fetch and validate Talos release metadata from GitHub."""
    request = Request(url, headers=github_headers())
    try:
        with urlopen(request, timeout=15) as response:
            release = json.load(response)
    except (OSError, URLError, json.JSONDecodeError) as error:
        raise DeploymentError("could not retrieve Talos release information from GitHub") from error

    if not isinstance(release, dict):
        raise DeploymentError("GitHub returned invalid Talos release information")
    return release


def release_version(release: dict[str, object]) -> str:
    """Extract and validate a stable version tag from release metadata."""
    version = release.get("tag_name")
    if not isinstance(version, str) or not re.fullmatch(r"v\d+\.\d+\.\d+", version):
        raise DeploymentError("GitHub returned an invalid Talos release version")
    return version


@lru_cache(maxsize=1)
def latest_release() -> dict[str, object]:
    """Return GitHub's latest stable Talos release metadata."""
    return fetch_release(TALOS_LATEST_RELEASE_URL)


@lru_cache(maxsize=1)
def talos_version() -> str:
    """Return the requested version or GitHub's latest stable Talos release."""
    configured_version = os.environ.get("TALOS_VERSION")
    if configured_version:
        if not re.fullmatch(r"v\d+\.\d+\.\d+", configured_version):
            raise DeploymentError("TALOS_VERSION must look like v1.13.9")
        return configured_version
    return release_version(latest_release())


def release_for_version(version: str) -> dict[str, object]:
    """Return release metadata for the selected Talos version."""
    if not os.environ.get("TALOS_VERSION"):
        release = latest_release()
        if release_version(release) == version:
            return release
    url = TALOS_RELEASE_BY_TAG_URL.format(version=quote(version, safe=""))
    release = fetch_release(url)
    if release_version(release) != version:
        raise DeploymentError("GitHub returned release information for the wrong tag")
    return release


def kubernetes_version(release: dict[str, object]) -> str:
    """Extract the kube-apiserver image version from Talos release notes."""
    body = release.get("body")
    if not isinstance(body, str):
        raise DeploymentError("Talos release information has no release notes")

    match = re.search(r"registry\.k8s\.io/kube-apiserver:(v\d+\.\d+\.\d+)", body)
    if match is None:
        raise DeploymentError("could not find the Kubernetes kube-apiserver image in Talos release notes")
    return match.group(1)


def sync_kubernetes_versions(version: str) -> None:
    """Update Kubernetes component image tags in all machine configurations."""
    config_paths = sorted(Path.cwd().glob("controlplane*.yaml"))
    config_paths.extend(sorted(Path.cwd().glob("worker*.yaml")))
    if not config_paths:
        raise DeploymentError("no controlplane*.yaml or worker*.yaml files were found")

    pending_updates: list[tuple[Path, str]] = []
    for path in config_paths:
        contents = path.read_text(encoding="utf-8")
        matches = list(KUBERNETES_IMAGE_PATTERN.finditer(contents))
        if not matches:
            raise DeploymentError(f"no Kubernetes component images found in {path}")
        if any(match.group("version") != version for match in matches):
            updated = KUBERNETES_IMAGE_PATTERN.sub(lambda match: f"{match.group('image')}:{version}", contents)
            pending_updates.append((path, updated))

    if not pending_updates:
        print(
            f"Kubernetes images in {len(config_paths)} machine configs already match {version}",
            flush=True,
        )
        return

    for path, contents in pending_updates:
        path.write_text(contents, encoding="utf-8")
        print(f"Updated Kubernetes images in {path} to {version}", flush=True)


def ova_path(version: str) -> str:
    """Return an overridden OVA location or its Image Factory URL."""
    return os.environ.get("OVA_PATH") or (
        f"https://factory.talos.dev/image/{TALOS_FACTORY_SCHEMATIC}/{version}/vmware-amd64.ova"
    )


def run_govc(*args: str, check: bool = True) -> int:
    """Run govc, returning its exit status."""
    completed = subprocess.run(("govc", *args), check=False)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode or 1)
    return completed.returncode


def upload_ova() -> None:
    """Import the desired Talos Linux OVA into a new content library."""
    version = talos_version()
    release = release_for_version(version)
    k8s_version = kubernetes_version(release)
    path = ova_path(version)
    print(f"Uploading Talos Linux OVA {version}: {path}", flush=True)
    print(f"Talos {version} includes Kubernetes {k8s_version}", flush=True)
    sync_kubernetes_versions(k8s_version)
    run_govc("library.create", CLUSTER_NAME)
    run_govc(
        "library.import",
        "-n",
        f"talos-{version}",
        CLUSTER_NAME,
        path,
    )


def encoded_machine_config(path: Path) -> str:
    """Return a machine configuration as single-line base64 text."""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def replace(role: str, node_number: int) -> None:
    """Destroy and recreate one control-plane or worker node."""
    version = talos_version()
    is_control_plane = role == "cp"
    role_name = "control plane" if is_control_plane else "worker"
    vm_role = "cp" if is_control_plane else "worker"
    vm_name = f"{CLUSTER_NAME}-{vm_role}-{node_number}"

    if is_control_plane:
        cpu = CONTROL_PLANE_CPU
        memory = CONTROL_PLANE_MEM
        disk = CONTROL_PLANE_DISK
        config_path = CONTROL_PLANE_MACHINE_CONFIG_PATHS[node_number - 1]
    else:
        cpu = WORKER_CPU
        memory = WORKER_MEM
        disk = WORKER_DISK
        config_path = WORKER_MACHINE_CONFIG_PATHS[node_number - 1]

    print(f"\ndestroying {role_name} node: {vm_name}", flush=True)
    # A missing VM is expected when creating a node for the first time.
    run_govc("vm.destroy", vm_name, check=False)

    print(f"\nlaunching {role_name} node: {vm_name}\n", flush=True)
    machine_config = encoded_machine_config(config_path)

    run_govc(
        "library.deploy",
        f"{CLUSTER_NAME}/talos-{version}",
        vm_name,
    )
    run_govc(
        "vm.change",
        "-c",
        cpu,
        "-m",
        memory,
        "-e",
        f"guestinfo.talos.config={machine_config}",
        "-e",
        "disk.enableUUID=1",
        "-vm",
        vm_name,
    )
    run_govc(
        "vm.disk.change",
        "-vm",
        vm_name,
        "-disk.name",
        "disk-1000-0",
        "-size",
        disk,
    )

    if "GOVC_NETWORK" not in os.environ:
        print("GOVC_NETWORK is unset, assuming default VM Network", flush=True)
    else:
        network = os.environ["GOVC_NETWORK"]
        print(f"GOVC_NETWORK set to {network}", flush=True)
        run_govc(
            "vm.network.change",
            "-vm",
            vm_name,
            "-net",
            network,
            "ethernet-0",
        )

    run_govc("vm.power", "-on", vm_name)
    run_govc(
        "object.mv",
        f"/Datacenter/vm/{vm_name}",
        "/Datacenter/vm/Kubernetes",
    )
    run_govc("ls", "/Datacenter/vm/Kubernetes")


def delete_ova() -> None:
    """Delete the cluster's content library."""
    run_govc("library.rm", CLUSTER_NAME)


def ova_library_exists() -> bool:
    """Return whether the cluster's content library exists."""
    completed = subprocess.run(
        ("govc", "library.ls"),
        check=False,
        stdout=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode or 1)

    libraries = {line.strip().strip("/") for line in completed.stdout.splitlines() if line.strip()}
    return CLUSTER_NAME.strip("/") in libraries


def update_ova() -> None:
    """Replace the cluster's OVA library when it exists, then upload it."""
    if ova_library_exists():
        print(f"OVA library {CLUSTER_NAME} exists; deleting it", flush=True)
        delete_ova()
    else:
        print(f"OVA library {CLUSTER_NAME} does not exist; nothing to delete", flush=True)
    upload_ova()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy or replace Talos nodes on VMware using govc.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("upload_ova", help="create and populate the OVA library")
    subparsers.add_parser("update_ova", help="replace the OVA library if it already exists")
    subparsers.add_parser("delete_ova", help="delete the OVA library")

    replace_parser = subparsers.add_parser("replace", help="replace one VM")
    replace_parser.add_argument("role", choices=("cp", "worker"))
    replace_parser.add_argument("node_number", type=int, choices=(1, 2, 3))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "upload_ova":
            upload_ova()
        elif args.command == "update_ova":
            update_ova()
        elif args.command == "delete_ova":
            delete_ova()
        else:
            replace(args.role, args.node_number)
    except DeploymentError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except FileNotFoundError as error:
        missing = error.filename or "required file"
        print(f"Error: {missing} was not found", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
