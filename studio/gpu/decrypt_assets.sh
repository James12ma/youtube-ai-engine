#!/usr/bin/env bash
# Decrypt a studio-assets/<run id> branch with one of the private keys matching studio/keys/*.pub.pem.
#   studio/gpu/decrypt_assets.sh <run_id> <private_key.pem> <recipient_name> <out_dir>
set -euo pipefail
run=$1 key=$2 who=$3 out=$4
tmp=$(mktemp -d)
git fetch -q origin "studio-assets/$run"
git archive FETCH_HEAD | tar -x -C "$tmp"
(cd "$tmp" && sha256sum -c --quiet SHA256SUMS)
openssl pkeyutl -decrypt -inkey "$key" -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 \
  -in "$tmp/$who.key.enc" -out "$tmp/kk"
mkdir -p "$out"
cat "$tmp"/pack.enc.part* | openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$tmp/kk" | tar -x -C "$out"
rm -rf "$tmp"
echo "decrypted to $out"
