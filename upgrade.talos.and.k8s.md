## Upgrade Talos and Kubernetes

When upgrading Kubernetes only, not Talos

https://docs.siderolabs.com/kubernetes-guides/advanced-guides/upgrading-kubernetes

To trigger a Kubernetes upgrade, issue a command specifying the version of Kubernetes to ugprade to, such as: `talosctl --nodes <controlplane node> upgrade-k8s --to ${k8s_release}`

Note that the `--nodes` parameter specifies the control plane node to send the API call to, but all members of the cluster will be upgraded.

```bash
talosctl --nodes 10.1.1.11 upgrade-k8s --to 1.35.1
```

---

Change Talos version and k8s version in `controlplane-x.yaml`, `worker-x.yaml`, `vmware.sh`

```bash
# Replace Talos version from 1.12.x to 1.12.4 on Linux
sed -i 's/:v1\.12\.[0-9]\+/:v1.12.4/g' controlplane*.yaml worker*.yaml
sed -i 's/v1\.12\.[0-9]\+/v1.12.4/g' vmware.sh vmware-deploy-node.sh

# Replace Talos version from 1.12.x to 1.12.4 on macOS
# Use `brew install gnu-sed` to install GNU sed
gsed -i 's/:v1\.12\.[0-9]\+/:v1.12.4/g' controlplane*.yaml worker*.yaml
gsed -i 's/v1\.12\.[0-9]\+/v1.12.4/g' vmware.sh vmware-deploy-node.sh

cat vmware-deploy-node.sh | grep TALOS_VERSION=

# Replace k8s version from 1.35.x to 1.35.1 on Linux
sed -i 's/:v1\.35\.[0-9]\+/:v1.35.1/g' controlplane*.yaml worker*.yaml

# Replace k8s version from 1.35.x to 1.35.1 on macOS
# Use `brew install gnu-sed` to install GNU sed
gsed -i s/:v1\.35\.[0-9]\+/:v1.35.1/g' controlplane*.yaml worker*.yaml

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

