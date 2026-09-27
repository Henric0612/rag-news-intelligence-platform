# Frontend testing

The repository contains 8 Unit modules, 6 Integration modules, one Playwright Browser E2E specification, one performance module, and one security module. File presence does not mean that every suite is a required CI check or has been validated.

## Required GitHub CI contract

From `Frontend/`, install the committed lockfile and run the authoritative entrypoint:

```bash
npm ci
npm run test:ci
npm run build
```

`test:ci` runs every intended `tests/unit/` and `tests/integration/` Vitest module in CI mode. This includes the API URL regression test and state/request/SSE contracts. An unhandled error or Promise rejection fails the run. The command removes stale report files before testing, then requires nonempty `coverage/junit.xml` and `coverage/lcov.info`; Vitest also prints a coverage summary. Report production is required, while coverage percentages are informational and have no blocking threshold.

Daily CI runs the production build and a separate full Frontend Docker image build. See [Phase C CI](../../Docs/Phase-C-CI.md) for the four required checks and the boundary between mocked software contracts and local real-AI validation.

## Other test assets

```bash
npm run test:unit:all
npm run test:integration:all
npm run test:performance:all
npm run test:security:all
```

Security and performance suites are outside `test:ci`; their presence is not evidence of CI success. `npm run test:all` and the legacy runner are broader local selectors, not required gates.

`tests/e2e/test-complete-flow.spec.js` is a deferred Playwright Browser E2E asset. Playwright is not in the committed Frontend lockfile, and browser installation, services, test data, and stable assertions still need preparation. Browser E2E is not run by GitHub CI and is not claimed as green. The `npm run test:e2e` script exists for future local work once its prerequisites are met.
