# JajaEngland Cydia Repository

General package repository for tweaks and apps by **JajaEngland**.

Add to Cydia:

```text
https://jajaengland.github.io/repo/
```

APT source line: `deb https://jajaengland.github.io/repo/ ./`

Receptor's source and releases remain in [jajaengland/Receptor](https://github.com/jajaengland/Receptor). The previous root source `https://jajaengland.github.io/` and original source `https://jajaengland.github.io/Receptor/` remain available for compatibility. After adding `/repo/`, users may remove old sources to avoid duplicate entries. Existing released `.deb` files are copied without modification.

The repository uses the owner's uploaded purple emblem as `repo/CydiaIcon.png`. Legacy Cydia retrieves source icons from that filename. Package-list icons are separate: older Cydia only loads their `Icon` fields from local `file:///` paths. **JajaEngland Repository Icons** installs those local images under `/Library/JajaEngland/Icons/`. Receptor 1.2.1 depends on it, or users can install it first to enable custom icons before installing individual tweaks. Close and reopen Cydia after installing/upgrading the icons package. See Cydia's [package icon implementation](https://github.com/autopear/Cydia/blob/master/MobileCydia.mm#L2867).

## Add or update a tweak

```sh
python3 scripts/update-repository.py /path/to/your-tweak_1.0_iphoneos-arm.deb
python3 scripts/verify.py
git add .
git commit -m "Add your-tweak 1.0"
git push
```

The generator accepts any package ID and derives architecture metadata from the pool. It writes the canonical package pool, indexes and static catalog under `repo/`. It also writes root compatibility indexes with `Filename: repo/debs/...`, allowing old root-source installations to update without duplicating new package files. It uses Debian version ordering to select the latest version shown for each package. Old versions remain downloadable. A published filename cannot be overwritten with different bytes, and conflicting contents for the same package/version/architecture are rejected.

For a package icon, depiction, source link or compatibility/testing note, add an entry keyed by package ID to `catalog.json`. Web image/HTML paths are relative to `repo/`. `icon` selects the website image, while `package_icon` can specify a local `file:///` path for Cydia's package list. Packages without catalog entries still appear with their name, description, architecture and direct download. The index can override Depiction/Icon fields without rebuilding already released packages. Change repository branding in `repository.json` and layout in `index.template.html`. Run `python3 scripts/update-repository.py` with no package argument to rebuild existing contents.

To update the local icons package, change its files/control under `packaging/repo-icons`, bump its version and output filename in `scripts/build-icons.sh`, then run that script in Linux/WSL. Import/reindex and commit the result. Do not overwrite an already published icons package with new bytes under the same version.

## Hosting and verification

GitHub Pages publishes `main:/` from this repository. `.nojekyll` keeps binary package/index files unchanged. HTTPS is enforced on this default GitHub Pages domain; some older Cydia clients may need newer TLS/certificate support. No custom HTTP host is configured.

This is a flat repository, not a `dists/` repository. Indexes include MD5, SHA1 and SHA256 checksums for older and newer clients. The Release file is unsigned; client trust requirements vary. Package compatibility, root installation and stability must be tested separately from these repository integrity checks.

`python3 scripts/verify.py --live` checks the live indexes and package bytes against this checkout. No credentials or signing keys belong in this public repository.
