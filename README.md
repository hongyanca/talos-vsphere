# Talos Kubernetes Cluster on VMware

This repository provides guide for setting up a Talos-based Kubernetes cluster on VMware. It is intended for users who want to deploy Kubernetes clusters with static IP addresses and custom hostnames.

The main documentation, `talos.vmware.k8s.md`, guides you through the process of preparing your environment and deploying Kubernetes nodes on VMware vSphere. The guide adapts official Talos documentation to cover advanced scenarios such as static networking and custom node hostnames.

For detailed, step-by-step instructions, please refer to the [talos.vmware.k8s.md](./talos.vmware.k8s.md) document.

For Talos and Kubernetes upgrade instructions, please refer to the [upgrade.talos.and.k8s.md](./upgrade.talos.and.k8s.md) document.

---

### Renew `kubectl` client certificate.

Check `kubectl` client certificate expiration date:

```bash
cat ~/.kube/config | grep client-certificate-data | cut -f2 -d : | tr -d ' ' | base64 -d | openssl x509 -text -out - | grep "Not After"
```

Backup `~/.kube/config`

```bash
cp ~/.kube/config ~/.kube/config.backup
```

Generate a new client certificate

```bash
talosctl kubeconfig ~/.kube/config --force
```

Check the client cert expiration date again:

```bash
cat ~/.kube/config | grep client-certificate-data | cut -f2 -d : | tr -d ' ' | base64 -d | openssl x509 -text -out - | grep "Not After"
```
