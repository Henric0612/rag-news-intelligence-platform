# Backend testing

The repository contains 36 Backend pytest modules: 13 unit, 5 integration, 8 API, 6 E2E, and 4 performance modules. This is an inventory of files, not a claim that every test is selected or passes in CI.

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

The `ci` marker identifies the approved deterministic subset: six environment, three model, four authentication-service, twelve authentication-API, seven health/readiness-API, two authentication-integration, five RAG failure-contract, and two vector-mapping tests. The initial inventory is 41 exact cases; the marker is the executable source of truth. Tests outside that marker remain local assets and may require models, network, state, or other environment setup.

CI requires successful test execution and valid, nonempty coverage XML and JUnit XML. Coverage collection and report generation are required; the percentage threshold is informational. `Backend/pytest.ini` does not enforce an 80% gate. CI uses temporary SQLite and mocked AI dependencies; it does not exercise real Ollama, GPU, embedding model loading, or end-to-end RAG quality.

## Local validation boundary

From `Backend/`, `python -m pytest tests/unit/`, `tests/api/`, `tests/integration/`, `tests/e2e/`, and `tests/performance/` select broader suites. Run them with their own prerequisites and inspect actual results; they are not required GitHub checks. The local `python run_tests.py` helper is separate from the authoritative CI command.

For workflow design, image validation, and real-AI evidence boundaries, see [Phase C CI](../../Docs/Phase-C-CI.md). Native and Compose setup are described in the [Backend README](../README.md).
