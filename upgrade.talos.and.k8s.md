## Upgrade Talos and Kubernetes

When upgrading Kubernetes only, not Talos

https://www.talos.dev/v1.11/kubernetes-guides/upgrading-kubernetes/

```bash
talosctl --nodes 10.1.1.11 upgrade-k8s --to 1.34.2
talosctl --nodes 10.1.1.12 upgrade-k8s --to 1.34.2
talosctl --nodes 10.1.1.13 upgrade-k8s --to 1.34.2
talosctl --nodes 10.1.1.21 upgrade-k8s --to 1.34.2
talosctl --nodes 10.1.1.22 upgrade-k8s --to 1.34.2
talosctl --nodes 10.1.1.23 upgrade-k8s --to 1.34.2
```

---

Change Talos version and k8s version in `controlplane-x.yaml`, `worker-x.yaml`, `vmware.sh`

```bash
# Replace Talos version from 1.11.x to 1.11.3 on Linux
sed -i 's/:v1\.11\.[0-9]\+/:v1.11.3/g' controlplane*.yaml worker*.yaml
sed -i 's/v1\.11\.[0-9]\+/v1.11.3/g' vmware.sh vmware-deploy-node.sh

# Replace Talos version from 1.11.x to 1.11.3 on macOS
# Use `brew install gnu-sed` to install GNU sed
gsed -i 's/:v1\.11\.[0-9]\+/:v1.11.3/g' controlplane*.yaml worker*.yaml
gsed -i 's/v1\.11\.[0-9]\+/v1.11.3/g' vmware.sh vmware-deploy-node.sh

cat vmware-deploy-node.sh | grep TALOS_VERSION=

# Replace k8s version from 1.34.x to 1.34.2 on Linux
sed -i 's/:v1\.34\.[0-9]\+/:v1.34.2/g' controlplane*.yaml worker*.yaml

# Replace k8s version from 1.34.x to 1.34.2 on macOS
# Use `brew install gnu-sed` to install GNU sed
gsed -i s/:v1\.34\.[0-9]\+/:v1.34.2/g' controlplane*.yaml worker*.yaml

cat controlplane.yaml | grep 'siderolabs/kubelet'
cat worker.yaml | grep 'siderolabs/kubelet'
```

Delete the old ova template in vSphere Content Libraries. Upload the latest version.

`govc` environment variables in `.env` file:

```
export GOVC_URL=https://192.168.0.14
export GOVC_USERNAME='ansible@vsphere.local'
export GOVC_PASSWORD='xxxxxxxxxx'
export GOVC_INSECURE=true
export GOVC_DATASTORE='datastore1'
export GOVC_NETWORK='LANSeg - 10.1.0.0'
```

```bash
source .env
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

