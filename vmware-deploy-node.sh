#!/bin/bash

set -e
# export GOVC_URL=https://192.168.0.14
# export GOVC_USERNAME='ansible@vsphere.local'
# export GOVC_PASSWORD='xxxxxxxxxxxxxxxx'
# export GOVC_INSECURE=true
# export GOVC_DATASTORE='datastore1'
# export GOVC_NETWORK='LANSeg - 10.1.0.0'

CLUSTER_NAME=${CLUSTER_NAME:=k8s}
TALOS_VERSION=${TALOS_VERSION:=v1.11.6}
OVA_PATH=${OVA_PATH:="https://factory.talos.dev/image/903b2da78f99adef03cbbd4df6714563823f63218508800751560d3bc3557e40/${TALOS_VERSION}/vmware-amd64.ova"}

CONTROL_PLANE_COUNT=${CONTROL_PLANE_COUNT:=3}
CONTROL_PLANE_CPU=${CONTROL_PLANE_CPU:=4}
CONTROL_PLANE_MEM=${CONTROL_PLANE_MEM:=8192}
CONTROL_PLANE_DISK=${CONTROL_PLANE_DISK:=11G}
CONTROL_PLANE_MACHINE_CONFIG_PATHS=("./controlplane-1.yaml" "./controlplane-2.yaml" "./controlplane-3.yaml")

WORKER_COUNT=${WORKER_COUNT:=3}
WORKER_CPU=${WORKER_CPU:=4}
WORKER_MEM=${WORKER_MEM:=8192}
WORKER_DISK=${WORKER_DISK:=11G}
WORKER_MACHINE_CONFIG_PATHS=("./worker-1.yaml" "./worker-2.yaml" "./worker-3.yaml")

upload_ova() {
  ## Import desired Talos Linux OVA into a new content library
  govc library.create ${CLUSTER_NAME}
  govc library.import -n talos-${TALOS_VERSION} ${CLUSTER_NAME} ${OVA_PATH}
}

replace() {
  # Argument Checking
  if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Error: Usage: replace <cp|worker> <node_number>" >&2
    return 1
  fi

  role="$1"
  node_number="$2"

  if [[ "$role" != "cp" && "$role" != "worker" ]]; then
    echo "Error: First argument must be 'cp' or 'worker'" >&2
    return 1
  fi

  if ! [[ "$node_number" =~ ^[1-3]$ ]]; then
    echo "Error: Second argument must be node number 1, 2, or 3" >&2
    return 1
  fi

  if [ "$role" == "cp" ]; then
    ## Create a control plane node and edit their settings
    i="$node_number"

    echo ""
    echo "destroying control plane node: ${CLUSTER_NAME}-cp-${i}"
    echo ""
    set +e
    govc vm.destroy ${CLUSTER_NAME}-cp-${i}
    set -e

    echo ""
    echo "launching control plane node: ${CLUSTER_NAME}-cp-${i}"
    echo ""

    #~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#
    CONTROL_PLANE_B64_MACHINE_CONFIG=$(cat ${CONTROL_PLANE_MACHINE_CONFIG_PATHS[$((i - 1))]} | base64 | tr -d '\n')

    govc library.deploy ${CLUSTER_NAME}/talos-${TALOS_VERSION} ${CLUSTER_NAME}-cp-${i}

    govc vm.change \
      -c ${CONTROL_PLANE_CPU} \
      -m ${CONTROL_PLANE_MEM} \
      -e "guestinfo.talos.config=${CONTROL_PLANE_B64_MACHINE_CONFIG}" \
      -e "disk.enableUUID=1" \
      -vm ${CLUSTER_NAME}-cp-${i}

    govc vm.disk.change -vm ${CLUSTER_NAME}-cp-${i} -disk.name disk-1000-0 -size ${CONTROL_PLANE_DISK}

    if [ -z "${GOVC_NETWORK+x}" ]; then
      echo "GOVC_NETWORK is unset, assuming default VM Network"
    else
      echo "GOVC_NETWORK set to ${GOVC_NETWORK}"
      govc vm.network.change -vm ${CLUSTER_NAME}-cp-${i} -net "${GOVC_NETWORK}" ethernet-0
    fi

    govc vm.power -on ${CLUSTER_NAME}-cp-${i}
    govc object.mv /Datacenter/vm/${CLUSTER_NAME}-cp-${i} /Datacenter/vm/Kubernetes
    govc ls /Datacenter/vm/Kubernetes

  else
    ## Create worker nodes and edit their settings
    i="$node_number"

    echo ""
    echo "destroying worker node: ${CLUSTER_NAME}-worker-${i}"
    echo ""
    set +e
    govc vm.destroy ${CLUSTER_NAME}-worker-${i}
    set -e

    echo ""
    echo "launching worker node: ${CLUSTER_NAME}-worker-${i}"
    echo ""

    #~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#~#
    WORKER_B64_MACHINE_CONFIG=$(cat ${WORKER_MACHINE_CONFIG_PATHS[$((i - 1))]} | base64 | tr -d '\n')

    govc library.deploy ${CLUSTER_NAME}/talos-${TALOS_VERSION} ${CLUSTER_NAME}-worker-${i}

    govc vm.change \
      -c ${WORKER_CPU} \
      -m ${WORKER_MEM} \
      -e "guestinfo.talos.config=${WORKER_B64_MACHINE_CONFIG}" \
      -e "disk.enableUUID=1" \
      -vm ${CLUSTER_NAME}-worker-${i}

    govc vm.disk.change -vm ${CLUSTER_NAME}-worker-${i} -disk.name disk-1000-0 -size ${WORKER_DISK}

    if [ -z "${GOVC_NETWORK+x}" ]; then
      echo "GOVC_NETWORK is unset, assuming default VM Network"
    else
      echo "GOVC_NETWORK set to ${GOVC_NETWORK}"
      govc vm.network.change -vm ${CLUSTER_NAME}-worker-${i} -net "${GOVC_NETWORK}" ethernet-0
    fi

    govc vm.power -on ${CLUSTER_NAME}-worker-${i}
    govc object.mv /Datacenter/vm/${CLUSTER_NAME}-worker-${i} /Datacenter/vm/Kubernetes
    govc ls /Datacenter/vm/Kubernetes
  fi

}

delete_ova() {
  govc library.rm ${CLUSTER_NAME}
}

"$@"
