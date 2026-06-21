### Renew `talosctl` Client Certificate

The `talosctl` client certificate in `talosconfig` expires after one year. When expired, `talosctl` commands fail with `rpc error: ... remote error: tls: expired certificate`. The Talos CA is valid for ten years, so the client certificate can be re-signed locally with the CA stored in `controlplane.yaml` — no cluster access required. The existing client key in `talosconfig` is reused; only the certificate is rotated.

Check the current client cert expiration date:

```
grep '        crt:' talosconfig | head -1 | awk '{print $2}' | base64 -d | openssl x509 -noout -dates
```

Backup `talosconfig` and `~/.talos/config`:

```
ts=$(date +%Y%m%d-%H%M%S)
cp talosconfig talosconfig.bak.$ts
[ -f ~/.talos/config ] && cp ~/.talos/config ~/.talos/config.bak.$ts
```

Set up a work directory and extract the Talos CA (`machine.ca` in `controlplane.yaml`, lines 10–11) and the existing client key from `talosconfig`:

```
WORK=$(mktemp -d)

sed -n '10p' controlplane.yaml | awk '{print $2}' | base64 -d > "$WORK/ca.crt"
sed -n '11p' controlplane.yaml | awk '{print $2}' | base64 -d > "$WORK/ca.key"
grep '        key:' talosconfig | head -1 | awk '{print $2}' | base64 -d > "$WORK/client.key"
```

The keys are Ed25519 in the legacy `ED25519 PRIVATE KEY` PEM format, which OpenSSL 3.x rejects. Re-wrap them as PKCS#8 (the body is already PKCS#8 DER — only the PEM tag needs to change):

```
for f in "$WORK/ca.key" "$WORK/client.key"; do
  sed 's/ED25519 //' "$f" > "$f.new" && mv "$f.new" "$f"
done

openssl pkey -in "$WORK/ca.key" -noout -text | head -1
openssl pkey -in "$WORK/client.key" -noout -text | head -1
```

Generate a CSR with the client key and sign it with the Talos CA for one year, matching the original extensions (`KeyUsage` = critical DigitalSignature, `ExtendedKeyUsage` = clientAuth):

```
cat > "$WORK/ext" <<'EOF'
keyUsage = critical, digitalSignature
extendedKeyUsage = clientAuth
authorityKeyIdentifier = keyid
EOF

openssl req -new -key "$WORK/client.key" -subj "/O=os:admin" -out "$WORK/client.csr"

openssl x509 -req -in "$WORK/client.csr" \
  -CA "$WORK/ca.crt" -CAkey "$WORK/ca.key" -CAcreateserial \
  -days 365 -sha256 -extfile "$WORK/ext" \
  -out "$WORK/client.crt"
```

Verify the new certificate chains to the Talos CA:

```
openssl verify -CAfile "$WORK/ca.crt" "$WORK/client.crt"
openssl x509 -in "$WORK/client.crt" -noout -subject -issuer -dates
```

Replace the `crt:` field in both `talosconfig` and `~/.talos/config`:

```
NEW_B64=$(base64 < "$WORK/client.crt" | tr -d '\n')

for tc in talosconfig ~/.talos/config; do
  [ -f "$tc" ] || continue
  awk -v new="$NEW_B64" '/^        crt:/{print "        crt: " new; next}1' "$tc" > "$tc.tmp" && mv "$tc.tmp" "$tc"
done

rm -rf "$WORK"
```

Verify the renewal against a live node:

```
talosctl --talosconfig talosconfig --nodes <node-ip> get extensions
```
