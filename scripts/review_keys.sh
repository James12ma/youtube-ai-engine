#!/usr/bin/env bash
# Owner-session helper for encrypted preview delivery (runs in Claude's session, never in CI).
#   keygen <dir>             -> <dir>/private.pem (stays local) and prints the base64 public key
#   decrypt <dir> <branch> <out>  -> downloads qa/<run> parts, verifies SHA256, decrypts, untars
set -euo pipefail
cmd=$1; dir=$2
case "$cmd" in
  keygen)
    umask 077; mkdir -p "$dir"
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out "$dir/private.pem" 2>/dev/null
    openssl pkey -in "$dir/private.pem" -pubout | base64 -w0 ;;
  decrypt)
    branch=$3; out=$4; repo=${REPO:-James12ma/youtube-ai-engine}
    work=$(mktemp -d); mkdir -p "$out"
    # Blob API (base64) — raw downloads of small binary files were sometimes altered in transit.
    gh api "repos/$repo/git/trees/$branch" --jq '.tree[]|"\(.path) \(.sha)"' | while read -r f sha; do
      gh api "repos/$repo/git/blobs/$sha" --jq .content | base64 -d > "$work/$f"
    done
    (cd "$work" && sha256sum -c SHA256SUMS --quiet)
    openssl pkeyutl -decrypt -inkey "$dir/private.pem" -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 \
      -in "$work/key.enc" -out "$work/k"
    cat "$work"/pack.enc.part* | openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$work/k" | tar -C "$out" -xf -
    rm -rf "$work"; ls -la "$out" ;;
  *) echo "usage: keygen <dir> | decrypt <dir> <branch> <out>"; exit 2 ;;
esac
