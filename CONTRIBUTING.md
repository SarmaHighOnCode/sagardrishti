# Contributing

Six people, four months, one repository. These rules exist because **integration failure ends more SIH projects than algorithmic difficulty does**.

## The one rule that matters

> ### Every Friday, `main` must run end to end and be demoable.

Not "nearly working." Actually running, on the cached scenario, start to finish.

Three excellent subsystems that have never been run together is the classic failure mode, and it only becomes visible in December when there is no time left. The weekly integration build is the defence. It is not a status meeting.

## Workflow

```bash
git checkout -b feat/m6-reachability-gate
# work
make lint && make test
git commit -m "feat(m6): add reachability gate"
git push -u origin feat/m6-reachability-gate
```

Open a PR. One reviewer. CI green. Never commit to `main`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`

Types: `feat` `fix` `docs` `refactor` `test` `chore` `perf`
Scopes: `m1`–`m7` `core` `ingest` `api` `worker` `web` `ais` `db` `infra` `docs`

```
feat(m6): add per-vessel baseline gap profile
fix(m1): assert 40 m/px GSD on inference tiles
docs(adr): record the Go/Python boundary
```

## Ownership

| Module | Owner |
|---|---|
| M1–M4 `sagar_sar`, `ml/` | SAR/ML lead |
| M5 `sagar_drift` | Ocean/drift lead |
| M4, M6, Go AIS plane | AIS/attribution lead |
| API, DB, worker, M7, CI, Docker | Backend/integration |
| `web/` | Frontend |
| `data/`, demo cache, docs, deck | Data ops + demo owner |

**Ask the owner before changing their module's public interface.** Anything else, open a PR.

## Frozen after 15 October

| Artefact | Change process |
|---|---|
| [`docs/api/API_CONTRACT.md`](docs/api/API_CONTRACT.md) | Integration lead sign-off. Additive changes preferred; never rename or remove |
| `db/schema/` | Integration lead sign-off |

Frontend and backend cannot both be moving in November.

## Definition of done

- [ ] Tests pass, new behaviour has a test
- [ ] `make lint` clean
- [ ] Module README updated if behaviour changed
- [ ] **Provenance emitted** if it is a pipeline module
- [ ] **Uncertainty carried** if it produces an inferred value
- [ ] No secrets, no data files, no hardcoded hex colours in `web/`
- [ ] A significant decision has an ADR

## Things that will be rejected in review

| Rejected | Why |
|---|---|
| A hex colour outside `web/src/styles/tokens.css` | The PDF generator reads the same tokens. Drift is a credibility failure |
| A pipeline module that skips provenance | Its output cannot go in a dossier |
| An inferred value without an uncertainty interval | Product principle 2 |
| A dataset adapter that does not verify GSD | [ADR 0002](docs/adr/0002-fixed-ground-sample-distance.md) — silent failure |
| Naive linear interpolation across an AIS gap | Invents positions, which then seed fabricated evidence |
| An excluded AIS record influencing a score | A vessel must never be suspect because its transponder is broken |
| Colour jitter or elastic deformation on SAR | Physically meaningless |
| A committed data file or `.env` | `data/` is ignored for a reason |
| The word "guilty" in user-facing output | We rank. We never accuse |

## Documentation

**A module without a README is not done.** A significant decision without an ADR will be re-litigated in November by someone who was not in the room.

Keep ADRs short: Context, Decision, Rationale, Consequences — with the negatives stated as plainly as the positives. An ADR listing only benefits is marketing.
