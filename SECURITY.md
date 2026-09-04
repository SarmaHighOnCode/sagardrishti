# Security

## Reporting

This is a Smart India Hackathon 2026 project, not production software. If you find a vulnerability, open a private issue or contact the maintainers directly rather than filing publicly.

## Secrets

**Credentials are never committed.** `.env` is git-ignored; [`.env.example`](.env.example) documents the required variables with empty values.

If a credential is committed:

1. **Rotate it immediately** at the provider — CDSE, CMEMS, CDS, Earthdata, AISStream
2. Then clean history

Rotation comes first. Assume anything pushed to a remote is compromised, and history rewriting does not un-publish it.

## Data handling

| Data | Sensitivity | Handling |
|---|---|---|
| Satellite imagery | Open (Copernicus, NASA) | No restriction |
| Forcing data | Open | No restriction |
| **AIS** | Public broadcast, but identifies real vessels and operators | See below |
| Model weights | Ours | No restriction |
| Evidence dossiers | **Names specific real vessels** | See below |

### AIS and dossiers name real vessels

AIS is publicly broadcast, but a document ranking a **named, real vessel** as a pollution suspect is a different artefact from raw position data.

Rules:

- **Never publish a dossier naming a real vessel** outside the team, a demo, or an evaluation context
- **Demo scenarios use synthetic vessels** wherever a suspect is being ranked. The one exception is MSC ELSA 3, where the incident and vessel are already a matter of public record and court proceedings
- **Every synthetic result is labelled `SYNTHETIC`** — on screen, in the dossier, on slides
- **No output ever uses the word "guilty."** The system ranks candidates with calibrated probabilities

This is not only an ethics point. A wrongful public accusation against a real operator would be a serious harm and would end the project's credibility.

## Scope

The system produces **investigative leads for authorised maritime enforcement**, not automated accusations. Design choices bias toward flagging fewer vessels with better evidence — see [`SCORING_MODEL.md`](docs/SCORING_MODEL.md) section 7.1.
