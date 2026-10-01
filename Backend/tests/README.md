# Backend testing

The repository contains 40 Backend pytest modules: 17 unit, 5 integration, 8 API, 6 E2E, and 4 performance modules. This is an inventory of files, not a claim that every test is selected or passes in CI.

## Required GitHub CI contract

Run from the repository root after installing `Backend/requirements.lock` with Python 3.13:

```bash
mkdir -p artifacts
python -m pytest -c Backend/pytest.ini Backend/tests -m ci \
  --cov=Backend \
  --cov-config=Backend/tests/.coveragerc \
  --cov-report=term-missing \
  --cov-report=xml:artifacts/backend-coverage.xml \
  --junitxml=artifacts/backend-junit.xml
```

The `ci` marker is the executable source of truth for the approved deterministic subset. Phase C started with 41 cases across environment, models, authentication, health/readiness, RAG failures and vector mappings. Phase D adds 24 foundation/schema/math/isolation cases, 9 retrieval/ranking cases, 8 answer/report/protocol cases and 29 observability cases. The D5 local contract run passed 111 cases; this records that run rather than imposing a fixed future test-count gate. Tests outside the marker remain local assets and may require models, network, state or other setup.

CI requires successful test execution and valid, nonempty coverage XML and JUnit XML. Coverage collection and report generation are required; the percentage threshold is informational. `Backend/pytest.ini` does not enforce an 80% gate. CI uses temporary SQLite and mocked AI dependencies; it does not exercise real Ollama, GPU, embedding model loading, or end-to-end RAG quality.

## Local validation boundary

From `Backend/`, `python -m pytest tests/unit/`, `tests/api/`, `tests/integration/`, `tests/e2e/`, and `tests/performance/` select broader suites. Run them with their own prerequisites and inspect actual results; they are not required GitHub checks. The local `python run_tests.py` helper is separate from the authoritative CI command.

For workflow design, image validation, and real-AI evidence boundaries, see [Phase C CI](../../Docs/Phase-C-CI.md). Native and Compose setup are described in the [Backend README](../README.md).

Phase D methodology, real-AI baseline provenance, native/isolated Compose reproduction and final-SHA acceptance are documented in [Phase D Evaluation](../../Docs/Phase-D-Evaluation.md). AI quality and latency values are informational; they are not new required checks.
