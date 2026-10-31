#!/usr/bin/env bash
set -euo pipefail
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
stage="$(mktemp -d /tmp/jaja-repo-icons.XXXXXX)"
trap 'case "$stage" in /tmp/jaja-repo-icons.*) rm -rf -- "$stage" ;; esac' EXIT
cp -R "$root/packaging/repo-icons/." "$stage/"
find "$stage" -type d -exec chmod 0755 {} +
find "$stage" -type f -exec chmod 0644 {} +
mkdir -p "$root/repo/debs"
destination="$root/repo/debs/com.jajaengland.repoicons_1.0_all.deb"
if [ -e "$destination" ]; then
    printf 'Refusing to overwrite a published icons package. Bump its version and output filename first.\n' >&2
    exit 1
fi
dpkg-deb --root-owner-group -Zgzip --build "$stage" "$destination"
