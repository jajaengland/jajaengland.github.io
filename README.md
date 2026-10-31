# JajaEngland Cydia Repository

General package repository for tweaks and apps by **JajaEngland**.

Add to Cydia:

```text
https://jajaengland.github.io/
```

APT source line: `deb https://jajaengland.github.io/ ./`

Receptor is the first package. Its source and releases remain in [jajaengland/Receptor](https://github.com/jajaengland/Receptor). The original source at `https://jajaengland.github.io/Receptor/` remains available; after adding this general source, users may remove the old source to avoid duplicate entries. Existing released `.deb` files are copied without modification.

## Add or update a tweak

```sh
python3 scripts/update-repository.py /path/to/your-tweak_1.0_iphoneos-arm.deb
python3 scripts/verify.py
git add .
git commit -m "Add your-tweak 1.0"
git push
```

The generator accepts any package ID and derives architecture metadata from the pool. It builds `Packages`, `Packages.gz`, `Packages.bz2`, `Release` checksums and the static package catalog. It uses Debian version ordering to select the latest version shown for each package. Old versions remain downloadable. A published filename cannot be overwritten with different bytes, and conflicting contents for the same package/version/architecture are rejected.

For a package icon, depiction, source link or compatibility/testing note, add an entry keyed by package ID to `catalog.json`. Paths are relative to the repository root; add the actual image/HTML files alongside them. Packages without catalog entries still appear with their name, description, architecture and direct download. The index can override Depiction/Icon URLs for a new host without rebuilding already released packages. Change repository branding in `repository.json` and layout in `index.template.html`. Run `python3 scripts/update-repository.py` with no package argument to rebuild existing contents.

## Hosting and verification

GitHub Pages publishes `main:/` from this repository. `.nojekyll` keeps binary package/index files unchanged. HTTPS is enforced on this default GitHub Pages domain; some older Cydia clients may need newer TLS/certificate support. No custom HTTP host is configured.

This is a flat repository, not a `dists/` repository. Indexes include MD5, SHA1 and SHA256 checksums for older and newer clients. The Release file is unsigned; client trust requirements vary. Package compatibility, root installation and stability must be tested separately from these repository integrity checks.

`python3 scripts/verify.py --live` checks the live indexes and package bytes against this checkout. No credentials or signing keys belong in this public repository.
