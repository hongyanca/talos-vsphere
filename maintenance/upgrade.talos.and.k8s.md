## Upgrade Talos and Kubernetes

When upgrading Kubernetes only, not Talos

https://docs.siderolabs.com/kubernetes-guides/advanced-guides/upgrading-kubernetes

To trigger a Kubernetes upgrade, issue a command specifying the version of Kubernetes to ugprade to, such as: `talosctl --nodes <controlplane node> upgrade-k8s --to ${k8s_release}`

Note that the `--nodes` parameter specifies the control plane node to send the API call to, but all members of the cluster will be upgraded.

```bash
talosctl --nodes 10.1.1.11 upgrade-k8s --to 1.36.3
```

---

For the shell workflow, change the Talos and Kubernetes versions in `controlplane-x.yaml`,
`worker-x.yaml`, and the shell deployment scripts. `vmware-deploy-node.py` automatically retrieves
the latest stable Talos release from GitHub and synchronizes the Kubernetes component images in all
`controlplane*.yaml` and `worker*.yaml` files during `upload_ova`; set `TALOS_VERSION` to override it
with a specific Talos version.

```bash
# Replace Talos version from 1.13.x to 1.13.9 on Linux
sed -i 's/:v1\.13\.[0-9]\+/:v1.13.9/g' controlplane*.yaml worker*.yaml
sed -i 's/v1\.13\.[0-9]\+/v1.13.9/g' vmware.sh vmware-deploy-node.sh

# Replace Talos version from 1.13.x to 1.13.9 on macOS
# Use `brew install gnu-sed` to install GNU sed
gsed -i 's/:v1\.13\.[0-9]\+/:v1.13.9/g' controlplane*.yaml worker*.yaml
gsed -i 's/v1\.13\.[0-9]\+/v1.13.9/g' vmware.sh vmware-deploy-node.sh

# Optional: pin the Python deployment script instead of using the latest stable release
export TALOS_VERSION=v1.13.9

# Replace k8s version from 1.36.x to 1.36.3 on Linux
sed -i 's/:v1\.36\.[0-9]\+/:v1.36.3/g' controlplane*.yaml worker*.yaml

# Replace k8s version from 1.36.x to 1.36.3 on macOS
# Use `brew install gnu-sed` to install GNU sed
gsed -i 's/:v1\.36\.[0-9]\+/:v1.36.3/g' controlplane*.yaml worker*.yaml

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

Choose either the shell or Python version:

```bash
# Shell (load .env into the current shell first)
source .env
./vmware-deploy-node.sh delete_ova
./vmware-deploy-node.sh upload_ova

# Python (automatically loads .env from the script's directory)
# It uses the latest stable Talos release unless TALOS_VERSION is set.
./vmware-deploy-node.py delete_ova
./vmware-deploy-node.py upload_ova

# Or perform the Python delete-if-present and upload steps with one command
./vmware-deploy-node.py update_ova
```

Replace one node at a time using either version.

```bash
# Shell
./vmware-deploy-node.sh replace worker 3
./vmware-deploy-node.sh replace worker 2
./vmware-deploy-node.sh replace worker 1
./vmware-deploy-node.sh replace cp 3
./vmware-deploy-node.sh replace cp 2
./vmware-deploy-node.sh replace cp 1

# Python
./vmware-deploy-node.py replace worker 3
./vmware-deploy-node.py replace worker 2
./vmware-deploy-node.py replace worker 1
./vmware-deploy-node.py replace cp 3
./vmware-deploy-node.py replace cp 2
./vmware-deploy-node.py replace cp 1
```
