#!/usr/bin/env python3
"""Import any .deb and rebuild the JajaEngland flat Cydia repository."""
import argparse
import bz2
from datetime import datetime, timezone
from email.utils import format_datetime
import gzip
import hashlib
import io
from pathlib import Path
import shutil
import tarfile
import json
import html

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "repo"


def control_text(path):
    data = path.read_bytes()
    if not data.startswith(b"!<arch>\n"):
        raise ValueError("Not a Debian package: " + str(path))
    offset = 8
    while offset + 60 <= len(data):
        header = data[offset:offset + 60]
        if header[58:60] != b"`\n":
            raise ValueError("Invalid ar member")
        name = header[:16].decode("ascii").strip().rstrip("/")
        size = int(header[48:58])
        start = offset + 60
        if name.startswith("control.tar"):
            with tarfile.open(fileobj=io.BytesIO(data[start:start + size]), mode="r:*") as archive:
                for member in archive:
                    if member.isfile() and member.name.lstrip("./") == "control":
                        return archive.extractfile(member).read().decode("utf-8").strip()
        offset = start + size + size % 2
    raise ValueError("No package control file: " + str(path))


def digest(data, algorithm):
    return hashlib.new(algorithm, data).hexdigest()


def fields_from_control(text):
    return dict(line.split(": ", 1) for line in text.splitlines() if line and not line[0].isspace() and ": " in line)


def version_compare(left, right):
    # Debian version ordering: epoch, upstream, revision; '~' precedes all.
    def split(value):
        epoch, rest = value.split(":", 1) if ":" in value else ("0", value)
        upstream, revision = rest.rsplit("-", 1) if "-" in rest else (rest, "0")
        return int(epoch), upstream, revision
    def order(char):
        if char == "~": return -1
        if not char: return 0
        return ord(char) if char.isalpha() else ord(char) + 256
    def compare_parts(a, b):
        while a or b:
            while (a and not a[0].isdigit()) or (b and not b[0].isdigit()):
                ca = a[0] if a and not a[0].isdigit() else ""
                cb = b[0] if b and not b[0].isdigit() else ""
                if order(ca) != order(cb): return -1 if order(ca) < order(cb) else 1
                if ca: a = a[1:]
                if cb: b = b[1:]
            a, b = a.lstrip("0"), b.lstrip("0")
            na = "".join(ch for ch in a[:next((i for i, ch in enumerate(a) if not ch.isdigit()), len(a))])
            nb = "".join(ch for ch in b[:next((i for i, ch in enumerate(b) if not ch.isdigit()), len(b))])
            if len(na) != len(nb): return -1 if len(na) < len(nb) else 1
            if na != nb: return -1 if na < nb else 1
            a, b = a[len(na):], b[len(nb):]
        return 0
    le, lu, lr = split(left)
    re, ru, rr = split(right)
    if le != re: return -1 if le < re else 1
    return compare_parts(lu, ru) or compare_parts(lr, rr)


def write_homepage(config, catalog, indexed):
    escape = html.escape
    latest = {}
    for package in indexed:
        identifier = package["Package"]
        if identifier not in latest or version_compare(package["Version"], latest[identifier]["Version"]) > 0:
            latest[identifier] = package
    cards = []
    for identifier in sorted(latest):
        package = latest[identifier]
        meta = catalog.get(identifier, {})
        image = '<img src="%s" width="64" height="64" alt="">' % escape(meta["icon"], quote=True) if meta.get("icon") else ""
        details = meta.get("depiction", package["Filename"])
        source = '<a href="%s">Source code</a> · ' % escape(meta["source"], quote=True) if meta.get("source") else ""
        cards.append('<article>%s<h2>%s <small>%s</small></h2><p>%s</p><p class="muted">%s</p><p class="stage">%s</p><p>%s<a href="%s">Details</a> · <a href="%s">Download .deb</a></p></article>' % (
            image, escape(package.get("Name", identifier)), escape(package["Version"]), escape(package.get("Description", "")),
            escape(meta.get("compatibility", package.get("Architecture", ""))), escape(meta.get("stage", "")), source,
            escape(details, quote=True), escape(package["Filename"], quote=True)))
    url = escape(config["url"], quote=True)
    template = (ROOT / "index.template.html").read_text(encoding="utf-8")
    output = template.replace("{{TITLE}}", escape(config["label"])).replace("{{SOURCE_URL}}", url).replace("{{PACKAGES}}", "\n".join(cards))
    (OUTPUT / "index.html").write_text(output, encoding="utf-8", newline="\n")


def write_indexes(output, packages, config, architectures):
    (output / "Packages").write_bytes(packages)
    (output / "Packages.gz").write_bytes(gzip.compress(packages, mtime=0))
    (output / "Packages.bz2").write_bytes(bz2.compress(packages))
    release = [
        "Origin: " + config["origin"], "Label: " + config["label"], "Suite: stable", "Codename: " + config["codename"],
        "Version: 1.0", "Architectures: " + " ".join(sorted(architectures)), "Components: main",
        "Description: " + config["description"], "Icon: " + config["url"] + config["icon"],
        "Date: " + format_datetime(datetime.now(timezone.utc), usegmt=True),
    ]
    for title, algorithm in [("MD5Sum", "md5"), ("SHA1", "sha1"), ("SHA256", "sha256")]:
        release.append(title + ":")
        for name in ["Packages", "Packages.gz", "Packages.bz2"]:
            data = (output / name).read_bytes()
            release.append(" %s %d %s" % (digest(data, algorithm), len(data), name))
    (output / "Release").write_text("\n".join(release) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", nargs="?", type=Path)
    args = parser.parse_args()
    config = json.loads((ROOT / "repository.json").read_text(encoding="utf-8"))
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    output = OUTPUT
    pool = output / "debs"
    pool.mkdir(parents=True, exist_ok=True)
    if args.package:
        package = args.package.resolve(strict=True)
        candidate = fields_from_control(control_text(package))
        identity = tuple(candidate[key] for key in ["Package", "Version", "Architecture"])
        for existing in pool.glob("*.deb"):
            fields = fields_from_control(control_text(existing))
            if tuple(fields[key] for key in ["Package", "Version", "Architecture"]) == identity and existing.read_bytes() != package.read_bytes():
                raise ValueError("This package/version/architecture is already published with different bytes; bump the version.")
        destination = pool / package.name
        if package != destination.resolve():
            if destination.exists() and destination.read_bytes() != package.read_bytes():
                raise ValueError("A different published package already uses this filename; bump its version.")
            if not destination.exists(): shutil.copyfile(package, destination)
    entries = []
    indexed = []
    architectures = set()
    seen = {}
    for path in sorted(pool.glob("*.deb")):
        data = path.read_bytes()
        control = control_text(path)
        fields = fields_from_control(control)
        if fields["Package"] in config.get("hidden_packages", []) or fields["Version"] in config.get("hidden_versions", {}).get(fields["Package"], []):
            continue
        identity = (fields["Package"], fields["Version"], fields["Architecture"])
        checksum = digest(data, "sha256")
        if identity in seen and seen[identity] != checksum:
            raise ValueError("Different package contents share the same ID/version/architecture: " + repr(identity))
        seen[identity] = checksum
        control = "\n".join(line for line in control.splitlines() if line.split(":", 1)[0] not in {"Filename", "Size", "MD5sum", "SHA1", "SHA256"})
        architectures.add(fields["Architecture"])
        meta = catalog.get(fields["Package"], {})
        # Repository depictions/icons may move without altering released .deb bytes.
        for field, key in [("Depiction", "depiction"), ("Icon", "icon")]:
            if meta.get(key) or (field == "Icon" and meta.get("package_icon")):
                control = "\n".join(line for line in control.splitlines() if not line.startswith(field + ":"))
                value = meta["package_icon"] if field == "Icon" and meta.get("package_icon") else config["url"] + meta[key]
                control += "\n" + field + ": " + value
        fields["Filename"] = path.relative_to(output).as_posix()
        indexed.append(fields)
        entries.append(control + "\n" + "\n".join([
            "Filename: " + path.relative_to(output).as_posix(),
            "Size: " + str(len(data)),
            "MD5sum: " + digest(data, "md5"),
            "SHA1: " + digest(data, "sha1"),
            "SHA256: " + digest(data, "sha256"),
        ]))
    packages = ("\n\n".join(entries) + "\n\n").encode("utf-8")
    write_indexes(output, packages, config, architectures)
    # Existing users of the previous root source keep receiving packages.
    # Prefix their relative filenames rather than duplicating new package files.
    compatibility = packages.replace(b"Filename: debs/", b"Filename: repo/debs/")
    write_indexes(ROOT, compatibility, config, architectures)
    shutil.copyfile(output / config["icon"], ROOT / "CydiaIcon.png")
    (output / ".nojekyll").touch()
    write_homepage(config, catalog, indexed)
    print("Updated flat Cydia repository: " + str(output))
    print("Source URL: " + config["url"])


if __name__ == "__main__":
    main()
