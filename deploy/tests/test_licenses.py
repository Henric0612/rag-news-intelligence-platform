import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from deploy.rag_delivery import license_scan
from deploy.rag_delivery.__main__ import main
from deploy.rag_delivery.build import BuildError
from deploy.rag_delivery.licenses import (
    CONCLUSION,
    LOCKFILE,
    LicenseError,
    build_inventory,
    classify,
    npm_inventory,
    parse_apk_list,
    parse_caddy_build_info,
)
from support import SHA, VERSION, build_evidence

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS = build_evidence()["inputs"]["models"]
APK_OUTPUT = """\
alpine-baselayout-3.7.2-r0 x86_64 {alpine-baselayout} (GPL-2.0-only) [installed]
ca-certificates-bundle-20260909-r0 x86_64 {ca-certificates} (MPL-2.0 AND MIT) [installed]
libcap2-2.78-r0 x86_64 {libcap} (BSD-3-Clause OR GPL-2.0-only) [installed]
musl-1.2.5-r23 x86_64 {musl} (MIT) [installed]
zlib-1.3.2-r0 x86_64 {zlib} (Zlib) [installed]
"""
BUILD_INFO = ("go\tgo1.26.8\npath\tcaddy\nmod\tcaddy\t(devel)\t\n"
              "dep\tgithub.com/caddyserver/caddy/v2\tv2.11.7\th1:abc=\n"
              "dep\tgolang.org/x/net\tv0.40.0\th1:def=\nbuild\t-buildmode=exe\n")
FRONTEND_INFO = "caddy_path=/usr/bin/caddy\ncaddy_sha256=" + "a" * 64 + "\nalpine_release=3.23.6\nnode=absent\n"


def scan(**overrides):
    data = {
        "os_release": "Debian GNU/Linux 13 (trixie)",
        "debian_packages": [
            {"name": "bash", "version": "5.2", "architecture": "amd64", "copyright_file": True,
             "copyright_format": "dep5", "licenses": ["GPL-3+"]},
            {"name": "zlib1g", "version": "1.3", "architecture": "amd64", "copyright_file": True,
             "copyright_format": "dep5", "licenses": ["Zlib"]},
            {"name": "libgomp1", "version": "14.2", "architecture": "amd64", "copyright_file": False,
             "copyright_format": None, "licenses": []},
            {"name": "tzdata", "version": "2026a", "architecture": "all", "copyright_file": True,
             "copyright_format": "not-machine-readable", "licenses": []},
        ],
        "python_distributions": [
            {"name": "flask", "version": "3.0.3", "license": None, "license_expression": None,
             "license_classifiers": ["License :: OSI Approved :: BSD License"], "location": "/usr/local"},
            {"name": "html2text", "version": "2024.2.26", "license": "GNU GPL 3", "license_expression": None,
             "license_classifiers": [], "location": "/usr/local"},
            {"name": "mystery", "version": "1.0", "license": "UNKNOWN", "license_expression": None,
             "license_classifiers": [], "location": "/usr/local"},
            {"name": "scipy", "version": "1.17", "license": "BSD text " * 40 + "GNU General Public License",
             "license_expression": None, "license_classifiers": [], "location": "/usr/local"},
        ],
        "cpython": {"version": "3.13.15", "license_file": "/usr/local/lib/python3.13/LICENSE.txt",
                    "license_file_present": True, "license_file_sha256": "b" * 64, "psf_license_v2_text": True},
        "models": [{"id": m["id"], "revision": m["revision"], "readme_present": True, "license": "apache-2.0"}
                   for m in MODELS.values()],
    }
    data.update(overrides)
    return data


def lockfile(packages=None):
    return json.dumps({"name": "frontend", "lockfileVersion": 3, "packages": packages or {
        "": {"name": "frontend", "version": "1.0.0"},
        "node_modules/vue": {"version": "3.5.22", "license": "MIT"},
        "node_modules/dompurify": {"version": "3.2.7", "license": "(MPL-2.0 OR Apache-2.0)"},
        "node_modules/vite": {"version": "7.1.0", "license": "MIT", "dev": True},
        "node_modules/odd-dev": {"version": "0.1.0", "dev": True},
        "node_modules/@esbuild/linux-x64": {"version": "0.25.0", "license": "MIT", "dev": True, "optional": True},
    }}).encode()


class FakeImageDocker:
    """Docker CLI fake for the inventory: image ids, the in-image scan and the Alpine commands."""

    def __init__(self, evidence, scan_doc=None, fail=None, apk=APK_OUTPUT, ids=None):
        self.evidence = evidence
        self.scan_doc = scan() if scan_doc is None else scan_doc
        self.fail = fail
        self.apk = apk
        self.ids = ids or {}
        self.commands = []

    def __call__(self, args, stdin_text=None):
        self.commands.append(args)
        if self.fail and self.fail in " ".join(args):
            raise BuildError(f"{' '.join(args[:3])} ... exited 1")
        image = next((a for a in args if a.startswith("ghcr.io/")), "")
        service = "backend" if "backend" in image else "frontend"
        if args[:3] == ["docker", "image", "inspect"]:
            return self.ids.get(service, self.evidence["images"][service]["image_id"]) + "\n"
        assert args[:2] == ["docker", "run"] and "--network" in args and "none" in args
        assert "--pull" in args and "never" in args
        if "python" in args:
            assert "def debian_packages" in stdin_text
            return "noise\n" + json.dumps(self.scan_doc) + "\n"
        if "apk" in args:
            return self.apk
        if args[-1] == "version":
            return "v2.11.7 h1:yj0Y4fYZGPkSvibBJ1sTWE33xC0fxztVyXEW5iIdUT4=\n"
        if args[-1] == "build-info":
            return BUILD_INFO
        return FRONTEND_INFO


def dry_run_evidence(lock_bytes):
    evidence = build_evidence()
    evidence["inputs"]["files"][LOCKFILE] = hashlib.sha256(lock_bytes).hexdigest()
    for service in ("backend", "frontend"):
        evidence["images"][service] = {
            "local_tags": [f"ghcr.io/henric0612/rag-news-{service}:sha-6e5af4a"],
            "image_id": f"sha256:{service[0] * 64}",
            "labels": {"org.opencontainers.image.licenses": "Apache-2.0"} if service == "frontend" else {},
        }
    return evidence


def collect(docker=None, lock_bytes=None, evidence=None, **docker_kwargs):
    lock_bytes = lock_bytes or lockfile()
    evidence = evidence or dry_run_evidence(lock_bytes)
    docker = docker or FakeImageDocker(evidence, **docker_kwargs)
    with tempfile.TemporaryDirectory() as root:
        (Path(root) / "Frontend").mkdir()
        (Path(root) / LOCKFILE).write_bytes(lock_bytes)
        return build_inventory(root, evidence, lambda: "2026-10-19T09:00:00Z", run=docker)


def categories(inventory):
    return {(f["component"], f["name"]): f["category"] for f in inventory["findings"]}


class ClassifyTest(unittest.TestCase):
    def test_categories(self):
        cases = {
            "copyleft": [["GPL-2.0-only"], ["LGPL-2.1+"], ["MPL-2.0 AND MIT"], ["BSD-3-Clause OR GPL-2.0-only"],
                         ["License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)"],
                         ["EPL-2.0"], ["CC-BY-SA-4.0"], ["AGPL-3.0"], ["GFDL-1.3+"], ["MIT", "GFDL-1.2"]],
            "restrictive": [["UNLICENSED"], ["SEE LICENSE IN LICENSE.txt"], ["Proprietary"], ["BUSL-1.1"],
                            ["CC-BY-NC-4.0"], ["BSD-4-Clause"], ["BSD-4-clause (University of California)"]],
            "missing": [[], [None], [""], ["UNKNOWN"], ["NOASSERTION"]],
            "unrecognized": [["Custom"], ["Dual License"], ["MIT", "other"], ["BSD-3-clause", "custom"],
                             ["Expat", "verbatim"], ["License :: OSI Approved :: MIT License", "Dual License"]],
            "permissive": [["MIT"], ["Apache-2.0"], ["BSD-3-Clause"], ["ISC"], ["PSF-2.0"], ["Zlib"],
                           ["Unlicense"], ["Public Domain"], ["Expat"], ["curl"], ["apache-2.0"],
                           ["License :: OSI Approved :: MIT License"], [None, "MIT"], ["UNKNOWN", "MIT"],
                           ["Expat", "public-domain"], ["BSD", "License :: OSI Approved :: BSD License"]],
        }
        for expected, values_list in cases.items():
            for values in values_list:
                with self.subTest(values=values):
                    self.assertEqual(classify(values), expected)

    def test_restrictive_words_in_full_texts_do_not_mask_permissive_licenses(self):
        zlib_text = "This software is provided 'as-is' ... including commercial applications ... " * 5
        self.assertEqual(classify([zlib_text + " Permission is granted to anyone ... zlib"]), "permissive")
        self.assertEqual(classify(["Redistribution and use in source and binary forms " * 10]), "permissive")
        self.assertEqual(classify(["BSD text " * 40 + "GNU General Public License"]), "copyleft")


class ParserTest(unittest.TestCase):
    def test_apk_list(self):
        packages = parse_apk_list(APK_OUTPUT)
        self.assertEqual(packages[1], {"name": "ca-certificates-bundle", "version": "20260909-r0",
                                       "architecture": "x86_64", "origin": "ca-certificates",
                                       "license": "MPL-2.0 AND MIT"})
        self.assertEqual([p["name"] for p in packages][-1], "zlib")

    def test_apk_list_failures(self):
        for output in ("", "WARNING: something\n", "musl-1.2.5 x86_64 {musl} (MIT) [installed]\n"):
            with self.subTest(output=output):
                with self.assertRaises(LicenseError):
                    parse_apk_list(output)

    def test_caddy_build_info(self):
        info = parse_caddy_build_info(BUILD_INFO)
        self.assertEqual(info["go"], "go1.26.8")
        self.assertEqual(info["dependencies"][0], {"module": "github.com/caddyserver/caddy/v2", "version": "v2.11.7"})
        with self.assertRaises(LicenseError):
            parse_caddy_build_info("path\tcaddy\n")


class NpmInventoryTest(unittest.TestCase):
    def test_lockfile_scopes_and_evidence_type(self):
        findings = []
        data = lockfile()
        npm = npm_inventory(data, hashlib.sha256(data).hexdigest(), findings)
        self.assertEqual(npm["lockfile"]["evidence_type"], "declarative_lockfile")
        self.assertEqual(npm["lockfile"]["counts"], {"production": 2, "development": 3})
        scopes = {p["name"]: p["scope"] for p in npm["lockfile"]["packages"]}
        self.assertEqual(scopes["vue"], "production")
        self.assertEqual(scopes["@esbuild/linux-x64"], "development")
        self.assertEqual(npm["installed_tree"]["status"], "NOT_COLLECTED")
        self.assertEqual(npm["installed_tree"]["evidence_type"], "installed_dependency_tree")
        self.assertEqual(len(npm["installed_tree"]["proposed_alternatives_for_human_review"]), 2)
        by_name = {f["name"]: f for f in findings}
        self.assertEqual(by_name["dompurify"]["category"], "copyleft")
        self.assertIs(by_name["dompurify"]["redistributed_in_image"], True)
        self.assertEqual(by_name["odd-dev"]["category"], "missing")
        self.assertIs(by_name["odd-dev"]["redistributed_in_image"], False)
        self.assertEqual(by_name["installed dependency tree"]["category"], "evidence-gap")

    def test_lockfile_must_match_the_build(self):
        with self.assertRaisesRegex(LicenseError, "sha256"):
            npm_inventory(lockfile(), "0" * 64, [])
        bad = b'{"lockfileVersion": 1, "dependencies": {}}'
        with self.assertRaises(LicenseError):
            npm_inventory(bad, hashlib.sha256(bad).hexdigest(), [])

    def test_repository_lockfile_is_inventoried(self):
        data = (REPO_ROOT / LOCKFILE).read_bytes()
        npm = npm_inventory(data, hashlib.sha256(data).hexdigest(), [])
        counts = npm["lockfile"]["counts"]
        self.assertGreater(counts["production"], 0)
        self.assertGreater(counts["development"], 0)
        self.assertEqual(sum(counts.values()), len(npm["lockfile"]["packages"]))


class InventoryTest(unittest.TestCase):
    def test_inventory_lists_findings_without_a_compliance_decision(self):
        inventory = collect()
        self.assertEqual(inventory["conclusion"], CONCLUSION)
        self.assertEqual(inventory["conclusion"], "PENDING_HUMAN_REVIEW")
        self.assertIsNone(inventory["compliance_decision"])
        self.assertIn("no licensing, compliance or redistribution decision", inventory["statement"])
        self.assertEqual((inventory["tag"], inventory["commit_sha"]), (VERSION, SHA))
        found = categories(inventory)
        self.assertEqual(found[("debian", "bash")], "copyleft")
        self.assertEqual(found[("debian", "libgomp1")], "missing-copyright-file")
        self.assertEqual(found[("debian", "tzdata")], "unrecognized")
        self.assertEqual(found[("python", "html2text")], "copyleft")
        self.assertEqual(found[("python", "mystery")], "missing")
        self.assertEqual(found[("python", "scipy")], "copyleft")
        self.assertEqual(found[("alpine", "alpine-baselayout")], "copyleft")
        self.assertEqual(found[("caddy", "caddy")], "unverified-binary")
        self.assertEqual(found[("oci-label", "org.opencontainers.image.licenses")], "inherited-label")
        self.assertNotIn(("debian", "zlib1g"), found)
        self.assertNotIn(("python", "flask"), found)
        self.assertEqual(inventory["summary"]["findings"], len(inventory["findings"]))
        long_text = next(f for f in inventory["findings"] if f["name"] == "scipy")["licenses"][0]
        self.assertEqual(set(long_text), {"excerpt", "length", "sha256"})
        self.assertEqual(inventory["frontend"]["runtime_node"], "absent")
        self.assertEqual(inventory["frontend"]["caddy"]["caddyserver_module"]["version"], "v2.11.7")

    def test_all_permissive_components_still_need_human_review(self):
        clean = scan(debian_packages=[scan()["debian_packages"][1]],
                     python_distributions=[scan()["python_distributions"][0]])
        inventory = collect(scan_doc=clean, apk="musl-1.2.5-r23 x86_64 {musl} (MIT) [installed]\n",
                            lock_bytes=lockfile({"node_modules/vue": {"version": "3.5.22", "license": "MIT"}}))
        self.assertEqual({f["category"] for f in inventory["findings"]},
                         {"unverified-binary", "inherited-label", "evidence-gap"})
        self.assertEqual(inventory["conclusion"], "PENDING_HUMAN_REVIEW")
        self.assertIsNone(inventory["compliance_decision"])

    def test_collection_failures_raise(self):
        cases = {
            "docker run fails": dict(fail="--entrypoint python"),
            "apk fails": dict(fail="--entrypoint apk"),
            "caddy build-info fails": dict(fail="build-info"),
            "empty Debian list": dict(scan_doc=scan(debian_packages=[])),
            "empty Python list": dict(scan_doc=scan(python_distributions=[])),
            "model mismatch": dict(scan_doc=scan(models=[])),
            "scan incomplete": dict(scan_doc={"debian_packages": []}),
            "unparsable apk": dict(apk="garbage\n"),
            "image id differs": dict(ids={"frontend": "sha256:" + "0" * 64}),
        }
        for name, kwargs in cases.items():
            with self.subTest(name):
                with self.assertRaises((LicenseError, BuildError)):
                    collect(**kwargs)

    def test_lockfile_hash_mismatch_fails(self):
        evidence = dry_run_evidence(lockfile())
        evidence["inputs"]["files"][LOCKFILE] = "0" * 64
        with self.assertRaisesRegex(LicenseError, "sha256"):
            collect(evidence=evidence)

    def test_cli_failure_exits_nonzero_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "build.json").write_text(json.dumps({"schema_version": 1, "images": {}}))
            out = tmp / "license-inventory.json"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
                code = main(["license-inventory", "--source-dir", str(REPO_ROOT),
                             "--build-evidence", str(tmp / "build.json"), "--out", str(out)])
            self.assertEqual(code, 1)
            self.assertIn("both images", err.getvalue())
            self.assertFalse(out.exists())


class LicenseScanScriptTest(unittest.TestCase):
    def write(self, text):
        handle = tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt")
        handle.write(text)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return handle.name

    def test_dep5_copyright_licenses(self):
        path = self.write("Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/\n\n"
                          "Files: *\nLicense: GPL-2+\n\nFiles: lib/*\nLicense:   LGPL-2.1+\n text\n"
                          "\nLicense: GPL-2+\n")
        self.assertEqual(license_scan.copyright_licenses(path), ("dep5", ["GPL-2+", "LGPL-2.1+"]))
        self.assertEqual(license_scan.copyright_licenses(self.write("This is free text.\nLicense: x\n")),
                         ("not-machine-readable", []))

    def test_model_card_front_matter(self):
        self.assertEqual(license_scan.front_matter_license(self.write("---\nlanguage: en\nlicense: apache-2.0\n---\n# x\n")),
                         "apache-2.0")
        self.assertIsNone(license_scan.front_matter_license(self.write("# no front matter\nlicense: mit\n")))

    def test_script_imports_only_stdlib(self):
        source = (REPO_ROOT / "deploy/rag_delivery/license_scan.py").read_text()
        imports = [line for line in source.splitlines() if line.startswith(("import ", "from "))]
        self.assertEqual(imports, ["import glob", "import hashlib", "import importlib.metadata", "import json",
                                   "import os", "import subprocess", "import sys"])


if __name__ == "__main__":
    unittest.main()
