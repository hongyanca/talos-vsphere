### Renew `kubectl` Client Certification

Check the client cert expiration date:

```
cat ~/.kube/config | grep client-certificate-data | cut -f2 -d : | tr -d ' ' | base64 -d | openssl x509 -text -out - | grep "Not After"
```

Backup `~/.kube/config`

```
cp ~/.kube/config ~/.kube/config.backup
```

Generate a new client certificate

```
talosctl kubeconfig ~/.kube/config --force
```

Check the client cert expiration date again:

```
cat ~/.kube/config | grep client-certificate-data | cut -f2 -d : | tr -d ' ' | base64 -d | openssl x509 -text -out - | grep "Not After"
```