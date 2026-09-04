# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- Repository scaffold: docs, module structure, ADRs, CI, Compose
- PRD v2.0 superseding v1.0
- NISAR as a data source (L-band public 20 July 2026 via ASF DAAC) — Phase 2 stretch, ingest path only
- Design system anchored on Blueprint, Palantir's open-source system, with exact tokens
- Go AIS data plane: `aisd` recorder, `aisgen` generator, shared `aiscodec` — [ADR 0005](docs/adr/0005-go-for-the-ais-data-plane.md)
- AIS gap factor corrections: data quality pre-filter, per-vessel baseline profile, coarse coverage proxy
- Dark-vessel coarse size bucket to avoid flagging AIS-exempt small craft
- ADRs 0001–0005

### Changed
- **Attribution method:** forward drift from every vessel is primary; backtracking secondary — [ADR 0001](docs/adr/0001-forward-drift-attribution.md)
- **AIS gap scoring:** redefined from *"gap exists near spill"* to deviation from the vessel's own baseline, discounted by coverage. The naive version produces false accusations
- INCOIS status corrected to OOSA v5.0 and SARAT
- Frontend direction replaced with an explicit Palantir-grade operator console
- Boundary-gradient loss promoted from optional ablation to recommended

### Notes
- Sentinel-1A operations terminated 29 June 2026. Constellation is S1C + S1D
- Bulk historical AIS for Indian waters remains unavailable. Synthetic generation is the plan, not a fallback

---

## Version policy

- `0.x` through the hackathon
- Bump PRD version and record reasoning in its changelog on every material change
- ADRs are never edited once accepted — supersede them
