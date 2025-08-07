## Upgrade Talos and Kubernetes

When upgrading Kubernetes only, not Talos

https://www.talos.dev/v1.10/kubernetes-guides/upgrading-kubernetes/

```bash
talosctl --nodes 10.1.1.11 upgrade-k8s --to 1.33.3
talosctl --nodes 10.1.1.12 upgrade-k8s --to 1.33.3
talosctl --nodes 10.1.1.13 upgrade-k8s --to 1.33.3
talosctl --nodes 10.1.1.21 upgrade-k8s --to 1.33.3
talosctl --nodes 10.1.1.22 upgrade-k8s --to 1.33.3
talosctl --nodes 10.1.1.23 upgrade-k8s --to 1.33.3
```

---

Change Talos version and k8s version in `controlplane-x.yaml`, `worker-x.yaml`, `vmware.sh`

```bash
# Replace Talos version from 1.10.x to 1.10.6
sed -i 's/:v1\.10\.[0-9]\+/:v1.10.6/g' controlplane*.yaml worker*.yaml
sed -i 's/v1\.10\.[0-9]\+/v1.10.6/g' vmware.sh vmware-deploy-node.sh
cat vmware-deploy-node.sh | grep TALOS_VERSION=

# Replace k8s version from 1.33.x to 1.33.3
sed -i 's/:v1\.33\.[0-9]\+/:v1.33.3/g' controlplane*.yaml worker*.yaml
```

Delete the old ova template in vSphere Content Libraries. Upload the latest version.

```bash
./vmware-deploy-node.sh delete_ova
./vmware-deploy-node.sh upload_ova 
```

Replace one node at a time.

```bash
./vmware-deploy-node.sh replace worker 3
./vmware-deploy-node.sh replace worker 2
./vmware-deploy-node.sh replace worker 1
./vmware-deploy-node.sh replace cp 3
./vmware-deploy-node.sh replace cp 2
./vmware-deploy-node.sh replace cp 1
```

