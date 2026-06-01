# Talos Kubernetes Cluster on VMware

This repository provides guide for setting up a [Talos-based Kubernetes cluster](https://github.com/siderolabs/talos) on VMware. It is intended for users who want to deploy Kubernetes clusters with static IP addresses and custom hostnames.

The main documentation, [Step-by-step Installation](./install/README.md), guides you through the process of preparing your environment and deploying Kubernetes nodes on VMware vSphere. The guide adapts official Talos documentation to cover advanced scenarios such as static networking and custom node hostnames.

- For detailed, step-by-step instructions, please refer to the [Step-by-step Installation](./install/README.md) document.
- For TrueNAS backed PVCs on Talos Kubernetes using Democratic CSI, please refer to the [NFS and iSCSI Configuration](storage/README.md) document.
- For Talos and Kubernetes upgrade instructions, please refer to the [maintenance/upgrade.talos.and.k8s.md](./maintenance/upgrade.talos.and.k8s.md) document.
- For `kubectl` client certification renewal, please refer to the [maintenance/renew.kubectl.client.cert.md](./maintenance/renew.kubectl.client.cert.md) document.
