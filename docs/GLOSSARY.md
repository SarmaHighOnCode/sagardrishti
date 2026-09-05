# Glossary

Terms used across this repository. Domain physics is covered more fully in [`DOMAIN_PRIMER.md`](DOMAIN_PRIMER.md).

## Remote sensing

| Term | Meaning |
|---|---|
| **SAR** | Synthetic Aperture Radar. Active microwave imaging; works day, night and through cloud |
| **sigma-nought / sigma-0** | Normalised radar cross-section. Calibrated backscatter, the quantity we actually measure |
| **Bragg scattering** | Resonant scattering from surface waves matching the radar wavelength. Why the sea is bright and oil is dark |
| **Marangoni damping** | Suppression of capillary waves by a surface film through surface-tension gradients |
| **Speckle** | Multiplicative interference noise inherent to coherent imaging |
| **Multilooking** | Averaging independent looks to reduce speckle at the cost of resolution |
| **Incidence angle** | Angle between the radar beam and the surface normal. Backscatter varies strongly across the swath |
| **GRD** | Ground Range Detected. Amplitude-only product with phase discarded |
| **IW** | Interferometric Wide swath. Sentinel-1's default mode over most seas, 250 km swath |
| **VV / VH** | Polarisation channels. VV is co-polarised and the workhorse; VH is cross-polarised and near the noise floor over water |
| **C-band** | ~5.6 cm wavelength. Sentinel-1 |
| **L-band** | ~24 cm wavelength. NISAR |
| **GSD** | Ground Sample Distance. Metres per pixel. **Fixed at 40 m/px throughout this project** |
| **COG** | Cloud-Optimized GeoTIFF. Internally tiled raster supporting partial HTTP reads |
| **STAC** | SpatioTemporal Asset Catalog. The metadata standard we use for scene discovery |
| **CFAR** | Constant False Alarm Rate. Adaptive-threshold detector used for ship point targets |
| **RFI** | Radio Frequency Interference. Appears as bright linear artefacts |

## Oil and ocean

| Term | Meaning |
|---|---|
| **Slick** | A surface oil film, whatever its origin |
| **Look-alike** | Any non-oil dark feature in SAR — low wind, biogenic film, internal waves, rain cells |
| **Biogenic film** | Natural surfactant layer from algae or plankton. The most common oil look-alike |
| **Damping ratio** | Background sigma-0 divided by slick sigma-0, in dB. Our mineral-oil indicator |
| **Weathering** | Evaporation, emulsification, dispersion and spreading. Irreversible — hence disabled in backward runs |
| **Emulsification** | Water-in-oil mixing forming *mousse*, changing viscosity and damping |
| **Lagrangian** | Following individual particles rather than a fixed grid. How drift is modelled |
| **Stokes drift** | Net transport from wave orbital motion |
| **Hindcast** | Backward-in-time reconstruction |
| **Wind drift factor** | Fraction of wind speed transferred to surface drift. Physically ~0.02–0.04; we sample the range |
| **Sub-mesoscale** | Ocean features 100 m – 10 km. Control slick shape; unresolved by our forcing. **Our dominant error term** |
| **CMEMS** | Copernicus Marine Environment Monitoring Service |
| **ERA5** | ECMWF's atmospheric reanalysis |
| **GEBCO** | General Bathymetric Chart of the Oceans |

## AIS and maritime

| Term | Meaning |
|---|---|
| **AIS** | Automatic Identification System. VHF broadcast of vessel identity, position and kinematics |
| **AIVDM** | The NMEA sentence format carrying AIS messages |
| **MMSI** | Maritime Mobile Service Identity. 9-digit vessel radio identifier. Frequently spoofed or reused |
| **IMO number** | Permanent 7-digit hull identifier. Does not change with ownership or flag |
| **SOG / COG** | Speed / Course Over Ground |
| **Class A / Class B** | Transponder classes. Class A is mandatory for larger commercial vessels and reports more often |
| **Dark vessel** | A vessel detected by sensor with no corresponding AIS broadcast |
| **AIS gap** | A period with no reports. **Not automatically suspicious** — see `SCORING_MODEL.md` section 2.1 |
| **Terrestrial AIS** | Shore-based receivers. Range roughly 40–75 nm. Explains most offshore gaps |
| **Satellite AIS** | Space-based receivers. Global but commercial, and out of scope for us |
| **Operational discharge** | Routine illegal release of tank washings, oily bilge or sludge. **The case this system is built for** |

## Institutions and regulation

| Term | Meaning |
|---|---|
| **NTRO** | National Technical Research Organisation. The problem statement owner |
| **ICG** | Indian Coast Guard. Central coordinating authority for oil spill response |
| **INCOIS** | Indian National Centre for Ocean Information Services. Runs OOSA and SARAT |
| **OOSA** | Online Oil Spill Advisory. INCOIS's operational service, now v5.0 |
| **SARAT** | Search and Rescue Aid Tool. INCOIS drift tool, activated for MSC ELSA 3 |
| **NOSDCP** | National Oil Spill Disaster Contingency Plan. India's response framework |
| **MARPOL Annex I** | IMO convention making operational oil discharge illegal |
| **EEZ** | Exclusive Economic Zone. 200 nautical miles |
| **CleanSeaNet** | EMSA's European SAR oil-detection service. Our closest analogue |
| **EMSA** | European Maritime Safety Agency |
| **CDSE** | Copernicus Data Space Ecosystem. Our Sentinel-1 source |
| **NISAR** | NASA-ISRO Synthetic Aperture Radar. L-band data public since 20 July 2026 |

## Project-specific

| Term | Meaning |
|---|---|
| **M1 – M7** | The seven pipeline modules. See [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| **Stage A / B / C** | Detection sub-stages: proposals, segmentation, physics filter |
| **Reachability region** | Backward-drift envelope used to gate irrelevant traffic |
| **drift_score** | Harmonic mean of plume hit and slick coverage, maximised over release time |
| **t-star (t\*)** | The inferred release time that best explains the observed slick |
| **Origin probability field** | 2D density of possible release locations. **Never a point** |
| **Evidence dossier** | Signed PDF with full provenance. M7 output |
| **Baseline gap profile** | A vessel's own normal gap behaviour, the reference for gap anomaly |
| **Data quality filter** | Pre-scoring exclusion of structurally invalid AIS records |
| **`aisd` / `aisgen`** | The Go AIS data plane — live recorder and synthetic generator, sharing a database writer (not a wire codec — see [ADR 0005](adr/0005-go-for-the-ais-data-plane.md)) |
