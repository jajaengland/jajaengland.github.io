#!/usr/bin/env python3
"""Check generic flat-repository checksums; optionally compare public hosted bytes."""
import argparse
import bz2
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "repo"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    config = json.loads((ROOT / "repository.json").read_text())
    catalog = json.loads((ROOT / "catalog.json").read_text())
    raw = (OUTPUT / "Packages").read_bytes()
    assert gzip.decompress((OUTPUT / "Packages.gz").read_bytes()) == raw
    assert bz2.decompress((OUTPUT / "Packages.bz2").read_bytes()) == raw
    paths = {"Packages", "Packages.gz", "Packages.bz2", "Release", "index.html"}
    count = 0
    identifiers = set()
    for entry in raw.decode().strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in entry.splitlines() if line and not line[0].isspace() and ": " in line)
        relative = Path(fields["Filename"])
        assert not relative.is_absolute() and ".." not in relative.parts
        data = (OUTPUT / relative).read_bytes()
        assert data.startswith(b"!<arch>\n") and len(data) == int(fields["Size"])
        for name, algorithm in [("MD5sum", "md5"), ("SHA1", "sha1"), ("SHA256", "sha256")]:
            assert fields[name] == hashlib.new(algorithm, data).hexdigest()
        expected_icon = catalog.get(fields["Package"], {}).get("package_icon")
        if expected_icon: assert fields["Icon"] == expected_icon
        paths.add(relative.as_posix())
        identifiers.add(fields["Package"])
        count += 1
    checks = 0
    for line in (OUTPUT / "Release").read_text().splitlines():
        if line in ["MD5Sum:", "SHA1:", "SHA256:"]:
            algorithm = {"MD5Sum:": "md5", "SHA1:": "sha1", "SHA256:": "sha256"}[line]
        elif line.startswith(" "):
            digest, size, name = line.split()
            data = (OUTPUT / name).read_bytes()
            assert len(data) == int(size) and hashlib.new(algorithm, data).hexdigest() == digest
            checks += 1
    assert checks == 9 and (ROOT / ".nojekyll").exists()
    assert "{{" not in (OUTPUT / "index.html").read_text()
    assert "Origin: " + config["origin"] in (OUTPUT / "Release").read_text()
    assert "Icon: " + config["url"] + config["icon"] in (OUTPUT / "Release").read_text()
    paths.add(config["icon"])
    for meta in catalog.values():
        for key in ["depiction", "icon"]:
            if meta.get(key):
                assert (OUTPUT / meta[key]).is_file()
                paths.add(meta[key])
    compatibility = (ROOT / "Packages").read_bytes()
    assert compatibility == raw.replace(b"Filename: debs/", b"Filename: repo/debs/")
    assert gzip.decompress((ROOT / "Packages.gz").read_bytes()) == compatibility
    assert bz2.decompress((ROOT / "Packages.bz2").read_bytes()) == compatibility
    for line in (ROOT / "Release").read_text().splitlines():
        if line in ["MD5Sum:", "SHA1:", "SHA256:"]:
            algorithm = {"MD5Sum:": "md5", "SHA1:": "sha1", "SHA256:": "sha256"}[line]
        elif line.startswith(" "):
            expected, size, name = line.split()
            data = (ROOT / name).read_bytes()
            assert len(data) == int(size) and hashlib.new(algorithm, data).hexdigest() == expected
    if args.live:
        for name in sorted(paths):
            with urllib.request.urlopen(config["url"] + name, timeout=30) as response:
                assert response.status == 200 and response.read() == (OUTPUT / name).read_bytes(), name
            print("PASS live: " + name)
        for name in ["Packages", "Packages.gz", "Packages.bz2", "Release", "CydiaIcon.png"]:
            with urllib.request.urlopen(urljoin(config["url"], "../") + name, timeout=30) as response:
                assert response.status == 200 and response.read() == (ROOT / name).read_bytes(), name
            print("PASS legacy root: " + name)
    print("PASS: %d versions across %d packages; compressed indexes, files and Release hashes verified" % (count, len(identifiers)))


if __name__ == "__main__":
    main()
