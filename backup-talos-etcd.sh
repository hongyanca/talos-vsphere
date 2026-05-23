#!/usr/bin/env bash

talosctl -n 10.1.1.10 etcd snapshot "etcd-$(date +%Y%m%d-%H%M).snapshot"
