"""Read-only third-party license inventory of the dry-run images (U10).

The inventory lists components and the licenses they declare, and records as
findings every copyleft, restrictive, missing or unrecognized license, every
missing Debian copyright file, and every evidence gap. It never decides that
the images are compliant or may be redistributed: ``conclusion`` is always
``PENDING_HUMAN_REVIEW`` and ``compliance_decision`` is always ``None``.

Any failure to collect or parse the data raises LicenseError, so the dry run
fails instead of publishing an incomplete inventory. Findings do not fail it.
"""

import hashlib
import json
import re
from pathlib import Path

from .build import run_command
from .contract import BUILD_EVIDENCE_SCHEMA_VERSION, SERVICES

LICENSE_SCAN_SCRIPT = Path(__file__).with_name("license_scan.py")
LOCKFILE = "Frontend/package-lock.json"
INVENTORY_SCHEMA_VERSION = 1
CONCLUSION = "PENDING_HUMAN_REVIEW"
STATEMENT = ("Read-only inventory for Human Review. Findings list items that need review; "
             "this document makes no licensing, compliance or redistribution decision.")
LONG_TEXT = 200

COPYLEFT_RE = re.compile(
    r"\b(?:a|l)?gpl|\bmpl\b|mpl-|\bepl\b|epl-|\bcddl|\beupl|\bosl-|\bcecill|cc-by-sa|copyleft"
    r"|general public licen[cs]e|mozilla public|eclipse public|share-?alike|\bgfdl|free documentation licen[cs]e",
    re.IGNORECASE)
RESTRICTIVE_RE = re.compile(
    r"\bproprietary\b|\bcommercial\b|non-?commercial|cc-by-nc|cc-by-nd|\bbusl\b|business source"
    r"|\bsspl\b|server side public|elastic license|\bunlicensed\b|see licen[cs]e in|bsd-4|4-clause",
    re.IGNORECASE)
PERMISSIVE_RE = re.compile(
    r"\bmit\b|\bexpat\b|\bbsd\b|bsd-|\b0bsd\b|apache|\bisc\b|\bpsf\b|psf-|python-2\.0"
    r"|python software foundation|\bzlib\b|\bunlicense\b|\bcc0|public[- ]domain|blueoak|cc-by-[34]"
    r"|\bhpnd\b|historical permission|\bx11\b|\bcurl\b|\bbzip2|\bwtfpl\b|\bmit-0\b"
    r"|permission is hereby granted|redistribution and use in source and binary forms",
    re.IGNORECASE)
ABSENT_VALUES = {"", "unknown", "none", "noassertion", "n/a"}

APK_LINE_RE = re.compile(r"(?P<nv>\S+) (?P<arch>\S+) \{(?P<origin>[^}]*)\} \((?P<license>.*)\) \[installed\]")
APK_VERSION_RE = re.compile(r"(?P<name>.+)-(?P<version>[^-]+-r[0-9]+)")
FRONTEND_INFO_SCRIPT = (
    'set -e; p="$(command -v caddy)"; echo "caddy_path=$p"; '
    'echo "caddy_sha256=$(sha256sum "$p" | cut -d" " -f1)"; '
    'echo "alpine_release=$(cat /etc/alpine-release)"; '
    'if command -v node >/dev/null 2>&1; then echo node=present; else echo node=absent; fi'
)
NPM_TREE_GAP = {
    "status": "NOT_COLLECTED",
    "evidence_type": "installed_dependency_tree",
    "reason": ("npm ls --all --json needs the installed node_modules tree, which exists only in the "
               "Frontend build stage; that stage is discarded by the multi-stage build and the runtime "
               "image (caddy:2-alpine) contains neither node nor node_modules. Running npm ls against "
               "any other tree would not describe the released bundle, so no installed-tree evidence "
               "is claimed."),
    "proposed_alternatives_for_human_review": [
        {
            "id": "build-stage-target",
            "method": ("In build-dry-run only: docker build --target build of Frontend/Dockerfile at the "
                       "same SHA (reusing the local BuildKit cache), docker run --network none of that "
                       "stage image for npm ls --all --json, and a fail-closed check that the stage's "
                       "/app/dist file digests equal /srv in the runtime image."),
            "boundary": "No Dockerfile, dependency or release-image change; adds one non-release image build.",
        },
        {
            "id": "runner-reinstall",
            "method": ("npm ci --ignore-scripts in a scratch copy of Frontend/ on the runner, then npm ls "
                       "--all --json; recorded as a reinstalled tree, not the image's tree."),
            "boundary": "Uses the runner's Node/npm and the npm registry; weaker evidence than the build stage.",
        },
    ],
}


class LicenseError(RuntimeError):
    """License data could not be collected or parsed; the inventory is not produced."""


def _present(value):
    return isinstance(value, str) and value.strip().lower() not in ABSENT_VALUES


def classify(values):
    """Category of a component from its declared license strings.

    ``copyleft`` or ``restrictive`` if any value matches; ``missing`` if
    nothing is declared; ``permissive`` only if every declared value is
    recognized as permissive; otherwise ``unrecognized``, so one unknown
    value is never hidden by a permissive one. Restrictive terms are matched only
    in short identifiers, not in full license texts, where words such as
    "commercial" occur in permissive licenses.
    """
    values = [v for v in values if _present(v)]
    if not values:
        return "missing"
    if any(COPYLEFT_RE.search(v) for v in values):
        return "copyleft"
    if any(len(v) <= LONG_TEXT and RESTRICTIVE_RE.search(v) for v in values):
        return "restrictive"
    if all(PERMISSIVE_RE.search(v) for v in values):
        return "permissive"
    return "unrecognized"


def _short(value):
    """Keep long license texts out of the inventory; record their digest instead."""
    if not isinstance(value, str) or len(value) <= LONG_TEXT:
        return value
    return {"excerpt": " ".join(value[:LONG_TEXT].split()) + " ...", "length": len(value),
            "sha256": hashlib.sha256(value.encode()).hexdigest()}


def _finding(findings, component, name, version, category, licenses, detail, redistributed=True):
    findings.append({"component": component, "name": name, "version": version, "category": category,
                     "licenses": licenses, "redistributed_in_image": redistributed, "detail": detail})


def _license_finding(findings, component, name, version, licenses, redistributed=True):
    """Classify the full license strings; record long texts in the finding by digest only."""
    category = classify(licenses)
    licenses = [_short(v) for v in licenses if _present(v)]
    if category != "permissive":
        detail = {
            "copyleft": "copyleft license terms present",
            "restrictive": "license may restrict redistribution",
            "missing": "no license declared",
            "unrecognized": "declared license not recognized",
        }[category]
        _finding(findings, component, name, version, category, licenses, detail, redistributed)
    return category


def _last_json_line(output, what):
    lines = [line for line in output.splitlines() if line.strip()]
    try:
        data = json.loads(lines[-1])
    except (IndexError, ValueError) as error:
        raise LicenseError(f"{what} produced no JSON result") from error
    if not isinstance(data, dict):
        raise LicenseError(f"{what} result is not an object")
    return data


# --- Backend ---

def backend_inventory(scan, expected_models, findings):
    """Classify the in-image scan of the Backend image (see license_scan.py)."""
    try:
        debian, python = scan["debian_packages"], scan["python_distributions"]
        cpython, models = scan["cpython"], scan["models"]
    except (KeyError, TypeError) as error:
        raise LicenseError(f"backend scan is incomplete: {error!r}") from error
    if not debian or not python:
        raise LicenseError(f"backend scan found {len(debian)} Debian packages and "
                           f"{len(python)} Python distributions; expected both to be non-empty")

    for package in debian:
        if not package.get("copyright_file"):
            _finding(findings, "debian", package["name"], package["version"], "missing-copyright-file",
                     [], f"/usr/share/doc/{package['name']}/copyright is missing")
        elif package.get("copyright_format") != "dep5":
            _finding(findings, "debian", package["name"], package["version"], "unrecognized", [],
                     "copyright file is not machine-readable (DEP-5); review the text manually")
        else:
            package["category"] = _license_finding(findings, "debian", package["name"],
                                                   package["version"], package["licenses"])

    distributions = []
    for dist in python:
        if not _present(dist.get("name")) or not _present(dist.get("version")):
            raise LicenseError(f"Python distribution without name or version at {dist.get('location')}")
        values = [dist.get("license_expression"), dist.get("license")] + list(dist.get("license_classifiers") or [])
        category = _license_finding(findings, "python", dist["name"], dist["version"], values)
        distributions.append(dict(dist, license=_short(dist.get("license")), category=category))

    if not cpython.get("license_file_present"):
        _finding(findings, "cpython", "CPython", cpython.get("version"), "missing", [],
                 f"{cpython.get('license_file')} not found in the image")
    elif not cpython.get("psf_license_v2_text"):
        _finding(findings, "cpython", "CPython", cpython.get("version"), "unrecognized", [],
                 "LICENSE.txt does not contain the PSF License Version 2 text")
    cpython = dict(cpython, license=("PSF-2.0 (in-image LICENSE.txt)" if cpython.get("psf_license_v2_text") else None))

    found = {(m.get("id"), m.get("revision")) for m in models}
    wanted = {(m["id"], m["revision"]) for m in expected_models.values()}
    if found != wanted:
        raise LicenseError(f"model snapshots {sorted(found)} != pinned models {sorted(wanted)}")
    for model in models:
        model["category"] = _license_finding(findings, "model", model["id"], model["revision"],
                                             [model.get("license")])

    return {"os_release": scan.get("os_release"), "debian_packages": debian,
            "python_distributions": distributions, "cpython": cpython, "models": models}


# --- Frontend ---

def parse_apk_list(output):
    packages = []
    for line in output.splitlines():
        if not line.strip():
            continue
        match = APK_LINE_RE.fullmatch(line.strip())
        version = APK_VERSION_RE.fullmatch(match.group("nv")) if match else None
        if not version:
            raise LicenseError(f"unparsable apk list line {line!r}")
        packages.append({"name": version.group("name"), "version": version.group("version"),
                         "architecture": match.group("arch"), "origin": match.group("origin"),
                         "license": match.group("license")})
    if not packages:
        raise LicenseError("apk list --installed returned no packages")
    return packages


def parse_caddy_build_info(output):
    info = {"go": None, "path": None, "main_module": None, "dependencies": []}
    for line in output.splitlines():
        fields = line.split("\t")
        if fields[0] == "go" and len(fields) > 1:
            info["go"] = fields[1]
        elif fields[0] == "path" and len(fields) > 1:
            info["path"] = fields[1]
        elif fields[0] == "mod" and len(fields) > 2:
            info["main_module"] = {"path": fields[1], "version": fields[2]}
        elif fields[0] == "dep" and len(fields) > 2:
            info["dependencies"].append({"module": fields[1], "version": fields[2]})
    if not info["go"] or not info["dependencies"]:
        raise LicenseError("caddy build-info output lacks the Go version or module list")
    return info


def parse_key_values(output, keys):
    values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    missing = [k for k in keys if not values.get(k)]
    if missing:
        raise LicenseError(f"frontend image info lacks {missing}")
    return values


def frontend_inventory(apk_output, caddy_version, build_info_output, info_output, labels, findings):
    packages = parse_apk_list(apk_output)
    for package in packages:
        package["category"] = _license_finding(findings, "alpine", package["name"], package["version"],
                                               [package["license"]])
    info = parse_key_values(info_output, ("caddy_path", "caddy_sha256", "alpine_release", "node"))
    if not caddy_version.strip():
        raise LicenseError("caddy version returned nothing")
    build_info = parse_caddy_build_info(build_info_output)
    caddy_module = next((d for d in build_info["dependencies"]
                         if d["module"] == "github.com/caddyserver/caddy/v2"), None)
    inherited = (labels or {}).get("org.opencontainers.image.licenses")
    _finding(findings, "caddy", "caddy", caddy_version.split()[0], "unverified-binary",
             [inherited] if inherited else [],
             (f"{info['caddy_path']} is installed outside apk; its license is only declared by the "
              f"inherited base-image label and is not confirmed from official Caddy sources; the "
              f"licenses of its {len(build_info['dependencies'])} embedded Go modules are not collected"))
    if inherited:
        _finding(findings, "oci-label", "org.opencontainers.image.licenses", None, "inherited-label",
                 [inherited], "inherited from caddy:2-alpine; describes Caddy, not this repository")
    return {
        "alpine_release": info["alpine_release"],
        "alpine_packages": packages,
        "caddy": {"path": info["caddy_path"], "sha256": info["caddy_sha256"],
                  "version_output": caddy_version.strip(), "caddyserver_module": caddy_module,
                  "build_info": build_info},
        "runtime_node": info["node"],
        "oci_licenses_label": inherited,
    }


def npm_inventory(lock_bytes, expected_sha256, findings):
    """Inventory from the declarative lockfile, bound to the hash recorded by the build."""
    actual = hashlib.sha256(lock_bytes).hexdigest()
    if actual != expected_sha256:
        raise LicenseError(f"{LOCKFILE} sha256 {actual} != build evidence {expected_sha256}")
    try:
        lock = json.loads(lock_bytes)
        entries = lock["packages"]
    except (ValueError, KeyError, TypeError) as error:
        raise LicenseError(f"{LOCKFILE} is not a lockfile with a packages map") from error
    if lock.get("lockfileVersion") not in (2, 3):
        raise LicenseError(f"{LOCKFILE} lockfileVersion {lock.get('lockfileVersion')!r} is unsupported")

    packages = []
    for path, entry in sorted(entries.items()):
        if path == "" or entry.get("link"):
            continue
        name = entry.get("name") or path.rsplit("node_modules/", 1)[-1]
        if not name or not entry.get("version"):
            raise LicenseError(f"{LOCKFILE} entry {path!r} lacks a name or version")
        dev_only = entry.get("dev") is True
        record = {"path": path, "name": name, "version": entry["version"], "license": entry.get("license"),
                  "scope": "development" if dev_only else "production",
                  "flags": sorted(k for k in ("dev", "optional", "devOptional", "peer") if entry.get(k) is True)}
        record["category"] = _license_finding(findings, "npm", name, entry["version"],
                                              [entry.get("license")], redistributed=not dev_only)
        packages.append(record)
    if not packages:
        raise LicenseError(f"{LOCKFILE} lists no packages")
    _finding(findings, "npm", "installed dependency tree", None, "evidence-gap", [],
             "npm ls --all --json was not run; see npm.installed_tree for the reason and the "
             "alternatives submitted for Human Review", redistributed=None)
    root = entries.get("", {})
    return {
        "lockfile": {
            "evidence_type": "declarative_lockfile",
            "path": LOCKFILE,
            "sha256": actual,
            "lockfile_version": lock["lockfileVersion"],
            "project_package": {"name": root.get("name"), "license": root.get("license")},
            "counts": {"production": sum(p["scope"] == "production" for p in packages),
                       "development": sum(p["scope"] == "development" for p in packages)},
            "packages": packages,
        },
        "installed_tree": dict(NPM_TREE_GAP),
    }


# --- Assembly ---

def summarize(findings):
    by_category, by_component = {}, {}
    for finding in findings:
        by_category[finding["category"]] = by_category.get(finding["category"], 0) + 1
        by_component[finding["component"]] = by_component.get(finding["component"], 0) + 1
    return {"findings": len(findings),
            "findings_redistributed_in_image": sum(f["redistributed_in_image"] is True for f in findings),
            "by_category": dict(sorted(by_category.items())),
            "by_component": dict(sorted(by_component.items()))}


def _image(build_evidence, service, run):
    image = build_evidence["images"][service]
    tag = image["local_tags"][0]
    image_id = run(["docker", "image", "inspect", "--format", "{{.Id}}", tag]).strip()
    if image_id != image["image_id"]:
        raise LicenseError(f"{tag} is {image_id}, build evidence recorded {image['image_id']}")
    return tag, image


def build_inventory(source_dir, build_evidence, now, run=run_command):
    """Collect the inventory of both dry-run images; raise LicenseError on any collection failure."""
    if build_evidence.get("schema_version") != BUILD_EVIDENCE_SCHEMA_VERSION:
        raise LicenseError("unsupported build evidence")
    if set(build_evidence.get("images") or {}) != set(SERVICES):
        raise LicenseError("build evidence does not describe both images")
    findings = []

    tag, _ = _image(build_evidence, "backend", run)
    scan = _last_json_line(run(["docker", "run", "--rm", "-i", "--pull", "never", "--network", "none",
                                "--entrypoint", "python", tag, "-"],
                               stdin_text=LICENSE_SCAN_SCRIPT.read_text()), "backend license scan")
    backend = backend_inventory(scan, build_evidence["inputs"]["models"], findings)
    backend.update(image=tag, image_id=build_evidence["images"]["backend"]["image_id"])

    tag, image = _image(build_evidence, "frontend", run)
    container = ["docker", "run", "--rm", "--pull", "never", "--network", "none", "--entrypoint"]
    frontend = frontend_inventory(
        run(container + ["apk", tag, "list", "--installed"]),
        run(container + ["caddy", tag, "version"]),
        run(container + ["caddy", tag, "build-info"]),
        run(container + ["sh", tag, "-c", FRONTEND_INFO_SCRIPT]),
        image.get("labels"), findings)
    frontend.update(image=tag, image_id=image["image_id"])
    frontend["npm"] = npm_inventory((Path(source_dir) / LOCKFILE).read_bytes(),
                                    build_evidence["inputs"]["files"][LOCKFILE], findings)

    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "kind": "license-inventory",
        "tag": build_evidence["tag"],
        "app_version": build_evidence["app_version"],
        "commit_sha": build_evidence["commit_sha"],
        "captured_at": now(),
        "conclusion": CONCLUSION,
        "compliance_decision": None,
        "statement": STATEMENT,
        "sources": [
            {"component": "debian", "evidence_type": "in_image_package_db",
             "method": "dpkg-query -W; /usr/share/doc/<package>/copyright presence and DEP-5 License fields"},
            {"component": "python", "evidence_type": "in_image_distribution_metadata",
             "method": "importlib.metadata: License, License-Expression, License :: classifiers"},
            {"component": "cpython", "evidence_type": "in_image_license_file",
             "method": "<sys.prefix>/lib/pythonX.Y/LICENSE.txt presence, sha256, PSF v2 text"},
            {"component": "model", "evidence_type": "in_image_model_card",
             "method": "license front matter of README.md in each pinned snapshot"},
            {"component": "alpine", "evidence_type": "in_image_package_db", "method": "apk list --installed"},
            {"component": "caddy", "evidence_type": "in_image_binary_and_inherited_label",
             "method": "caddy version, caddy build-info, sha256 of the binary, OCI licenses label"},
            {"component": "npm", "evidence_type": "declarative_lockfile",
             "method": f"{LOCKFILE} packages map at the commit, sha256-bound to the build evidence"},
        ],
        "notes": ["The repository has no LICENSE file (H3); project code is not a third-party finding."],
        "backend": backend,
        "frontend": frontend,
        "findings": findings,
        "summary": summarize(findings),
    }
