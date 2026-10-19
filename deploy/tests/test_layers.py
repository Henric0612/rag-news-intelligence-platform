import json
import unittest

from deploy.rag_delivery.build import BuildError
from deploy.rag_delivery.layers import LayerError, layer_evidence, parse_history, summarize
from deploy.rag_delivery.manifest import build_manifest, manifest_errors
from support import SHA, VERSION, build_evidence, gate_evidence, mutate, quiet, registry_images, valid_manifest


def history_line(created_by, size):
    return json.dumps({"Comment": "buildkit.dockerfile.v0", "CreatedAt": "2026-10-18T22:45:29+02:00",
                       "CreatedBy": created_by, "ID": "<missing>", "Size": str(size)})


HISTORY = {
    "backend": [("CMD [\"gunicorn\"]", 0), ("COPY /opt/huggingface /opt/huggingface", 1775644672),
                ("COPY /install /usr/local", 1500000000), ("RUN apt-get install libgomp1", 3000000)],
    "frontend": [("EXPOSE [3000/tcp]", 0), ("COPY /app/dist /srv", 2998272), ("RUN caddy install", 51970048)],
}


class FakeLayerDocker:
    def __init__(self, evidence, history=None, ids=None, fail=None):
        self.evidence = evidence
        self.history = history or {s: "\n".join(history_line(c, n) for c, n in rows) + "\n"
                                   for s, rows in HISTORY.items()}
        self.ids = ids or {}
        self.fail = fail
        self.commands = []

    def __call__(self, args, stdin_text=None):
        self.commands.append(args)
        if self.fail and self.fail in args:
            raise BuildError(f"{' '.join(args[:3])} ... exited 1")
        if args[:2] == ["docker", "info"]:
            return '"overlayfs"\n' if ".Driver}}" in args[-1] else '[["driver-type","io.containerd.snapshotter.v1"]]\n'
        service = "backend" if "backend" in args[-1] else "frontend"
        if args[:3] == ["docker", "image", "inspect"]:
            image_id = self.ids.get(service, self.evidence["images"][service]["image_id"])
            return json.dumps([{"Id": image_id, "Size": 5787700391 if service == "backend" else 96679804,
                                "RootFS": {"Layers": ["sha256:" + "1" * 64] * 3}}])
        if args[:2] == ["docker", "history"]:
            assert "--human=false" in args and "--no-trunc" in args
            return self.history[service]
        raise AssertionError(args)


def dry_run_build():
    evidence = build_evidence()
    for service in ("backend", "frontend"):
        evidence["images"][service] = {"local_tags": [f"ghcr.io/henric0612/rag-news-{service}:sha-6e5af4a"],
                                       "image_id": f"sha256:{service[0] * 64}"}
    return evidence


def measure(docker=None, evidence=None, **kwargs):
    evidence = evidence or dry_run_build()
    docker = docker or FakeLayerDocker(evidence, **kwargs)
    return quiet(layer_evidence, evidence, lambda: "2026-10-19T09:00:00Z", run=docker)


class LayerEvidenceTest(unittest.TestCase):
    def test_build_side_measurement_and_explicit_semantics(self):
        evidence = measure()
        backend = evidence["images"]["backend"]
        self.assertEqual(backend["max_local_layer_bytes"], 1775644672)
        self.assertEqual(backend["max_local_layer_created_by"], "COPY /opt/huggingface /opt/huggingface")
        self.assertEqual(backend["history_total_bytes"], 1775644672 + 1500000000 + 3000000)
        self.assertEqual(backend["nonzero_layer_count"], 3)
        self.assertEqual(backend["inspect_size_bytes"], 5787700391)
        self.assertEqual(evidence["images"]["frontend"]["max_local_layer_bytes"], 51970048)
        self.assertEqual(evidence["measurement"]["unit"], "bytes")
        self.assertIn("build-side, local layer size", evidence["measurement"]["semantics"])
        self.assertIn("depends on image_store", evidence["measurement"]["semantics"])
        self.assertIn("only after push", evidence["measurement"]["not_registry_values"])
        self.assertEqual(evidence["image_store"]["driver_status"], [["driver-type", "io.containerd.snapshotter.v1"]])
        self.assertEqual((evidence["tag"], evidence["commit_sha"]), (VERSION, SHA))

    def test_layer_evidence_never_uses_registry_field_names(self):
        evidence = measure()
        for service in ("backend", "frontend"):
            self.assertFalse({"max_layer_bytes", "compressed_size_bytes", "digest", "media_type"}
                             & set(evidence["images"][service]))

    def test_failures_raise(self):
        bad_history = {"backend": "not json\n", "frontend": history_line("x", 1)}
        for name, kwargs in {
            "image id differs": dict(ids={"backend": "sha256:" + "0" * 64}),
            "unparsable history": dict(history=bad_history),
            "history command fails": dict(fail="history"),
        }.items():
            with self.subTest(name):
                with self.assertRaises((LayerError, BuildError)):
                    measure(**kwargs)
        with self.assertRaises(LayerError):
            measure(evidence=dict(dry_run_build(), images={"backend": dry_run_build()["images"]["backend"]}))

    def test_history_parsing(self):
        self.assertEqual(parse_history(history_line("RUN x", 12) + "\n\n"), [{"created_by": "RUN x", "size_bytes": 12}])
        for output in ("", json.dumps({"Size": "12MB"}), json.dumps({"CreatedBy": "x"}), json.dumps({"Size": "-1"})):
            with self.subTest(output=output):
                with self.assertRaises(LayerError):
                    parse_history(output)
        with self.assertRaises(LayerError):
            summarize([{"created_by": "LABEL x", "size_bytes": 0}])


class RegistryFieldIsolationTest(unittest.TestCase):
    """Build-side layer sizes never reach the release manifest's registry fields."""

    def test_manifest_layer_fields_come_from_the_registry_only(self):
        polluted = build_evidence()
        for service in ("backend", "frontend"):
            polluted["images"][service].update(max_layer_bytes=1, compressed_size_bytes=2,
                                               max_local_layer_bytes=3, local_layers={"max": 4})
        registry = registry_images()
        manifest = build_manifest(gate_evidence(), polluted, registry)
        self.assertEqual(manifest, valid_manifest())
        for service in ("backend", "frontend"):
            self.assertEqual(manifest["images"][service]["max_layer_bytes"], registry[service]["max_layer_bytes"])
            self.assertEqual(manifest["images"][service]["compressed_size_bytes"],
                             registry[service]["compressed_size_bytes"])

    def test_release_schema_rejects_local_layer_fields(self):
        for field in ("max_local_layer_bytes", "local_layers", "history_total_bytes"):
            with self.subTest(field=field):
                errors = manifest_errors(mutate(valid_manifest(), f"images.backend.{field}", 1))
                self.assertIn(f"images.backend.{field}: unknown field", errors)


if __name__ == "__main__":
    unittest.main()
