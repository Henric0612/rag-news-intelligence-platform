"""Read-only license data collection, run inside the Backend image.

Executed as ``docker run --rm -i --network none --entrypoint python <image> -``
with this file on stdin, like declared_schema.py. It uses only the standard
library, writes nothing, and prints one JSON document as its last line:
Debian packages with their copyright files, installed Python distributions,
the CPython license file and the license front matter of the bundled model
snapshots. Classification happens outside the image, in licenses.py.
"""

import glob
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys

DPKG_FORMAT = "${db:Status-Abbrev}\t${Package}\t${Version}\t${Architecture}\n"
MODEL_SNAPSHOTS = "/opt/huggingface/hub/models--*/snapshots/*"
PSF_MARKER = "PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2"


def copyright_licenses(path):
    """(format, license short names) of a Debian copyright file."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    first = next((line for line in text.splitlines() if line.strip()), "")
    if not (first.startswith("Format:") and ("copyright-format" in first or "dep5" in first)):
        return "not-machine-readable", []
    names = set()
    for line in text.splitlines():
        if line.startswith("License:"):
            value = " ".join(line[len("License:"):].split())
            if value:
                names.add(value)
    return "dep5", sorted(names)


def debian_packages():
    output = subprocess.run(["dpkg-query", "-W", "-f", DPKG_FORMAT],
                            check=True, stdout=subprocess.PIPE, text=True).stdout
    packages = []
    for line in output.splitlines():
        status, name, version, arch = line.split("\t")
        if not status.startswith("ii"):
            continue
        path = f"/usr/share/doc/{name}/copyright"
        present = os.path.isfile(path)
        fmt, licenses = copyright_licenses(path) if present else (None, [])
        packages.append({"name": name, "version": version, "architecture": arch,
                         "copyright_file": present, "copyright_format": fmt, "licenses": licenses})
    return packages


def python_distributions():
    result = []
    for dist in importlib.metadata.distributions():
        meta = dist.metadata
        result.append({
            "name": meta["Name"],
            "version": meta["Version"],
            "license": meta.get("License"),
            "license_expression": meta.get("License-Expression"),
            "license_classifiers": sorted(c for c in (meta.get_all("Classifier") or [])
                                          if c.startswith("License ::")),
            "license_files": sorted(meta.get_all("License-File") or []),
            "location": str(dist.locate_file("")),
        })
    return sorted(result, key=lambda d: ((d["name"] or "").lower(), d["version"] or "", d["location"]))


def cpython():
    path = os.path.join(sys.prefix, "lib", f"python{sys.version_info[0]}.{sys.version_info[1]}", "LICENSE.txt")
    info = {"version": sys.version.split()[0], "license_file": path, "license_file_present": os.path.isfile(path)}
    if info["license_file_present"]:
        data = open(path, "rb").read()
        info["license_file_sha256"] = hashlib.sha256(data).hexdigest()
        info["psf_license_v2_text"] = PSF_MARKER.encode() in data
    return info


def front_matter_license(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("license:"):
            return line[len("license:"):].strip().strip("'\"") or None
    return None


def models():
    result = []
    for snapshot in sorted(glob.glob(MODEL_SNAPSHOTS)):
        repo_dir = snapshot.split("/snapshots/")[0].rsplit("/", 1)[1]
        readme = os.path.join(snapshot, "README.md")
        present = os.path.isfile(readme)
        result.append({
            "id": repo_dir[len("models--"):].replace("--", "/"),
            "revision": os.path.basename(snapshot),
            "readme_present": present,
            "license": front_matter_license(readme) if present else None,
        })
    return result


def os_release():
    try:
        with open("/etc/os-release") as handle:
            pairs = dict(line.split("=", 1) for line in handle.read().splitlines() if "=" in line)
    except OSError:
        return None
    return pairs.get("PRETTY_NAME", "").strip('"') or None


def main():
    print(json.dumps({
        "os_release": os_release(),
        "debian_packages": debian_packages(),
        "python_distributions": python_distributions(),
        "cpython": cpython(),
        "models": models(),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
