## What

<!-- One or two sentences. What changes and why. -->

## Module

<!-- M1-M7, core, ingest, api, worker, web, ais, db, infra, docs -->

## Checklist

- [ ] Tests pass; new behaviour has a test
- [ ] `make lint` clean
- [ ] Module README updated if behaviour changed
- [ ] ADR added if this is a significant decision

### If this touches a pipeline module

- [ ] Emits `ProvenanceRecord` — output that cannot be traced cannot go in a dossier
- [ ] Inferred values carry their uncertainty interval
- [ ] GSD assertion intact where rasters are handled

### If this touches attribution or AIS

- [ ] No single factor can independently produce a suspect
- [ ] Excluded/unreliable records do not shift a score in either direction
- [ ] Missing factors are dropped, not imputed
- [ ] No naive linear interpolation across AIS gaps

### If this touches the frontend

- [ ] No hex literal outside `web/src/styles/tokens.css`
- [ ] Identifiers monospace; timestamps ISO 8601 UTC; coordinates via `lib/format.ts`
- [ ] No CDN reference — offline mode must hold
- [ ] Uncertainty rendered, not flattened

### Always

- [ ] No secrets, no data files committed
- [ ] No user-facing text implies guilt. We rank, we never accuse

## Contract impact

<!-- After 15 October, API and schema changes need integration lead sign-off. -->

- [ ] No change to the API contract or DB schema
- [ ] Changes them, and the integration lead has signed off
