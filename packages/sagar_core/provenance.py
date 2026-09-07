"""Provenance capture: hashing, config snapshots, lineage records.

The rule this module exists to enforce (docs/ARCHITECTURE.md §4.3):
**provenance is captured as the pipeline runs, never reconstructed
afterwards.** M7 cannot go back and work out which model weights
produced a detection three stages ago — by then the information is gone.
Each module emits a ProvenanceRecord into the job context as it
executes, and M7 assembles them into the dossier's lineage page.

Why this matters beyond tidiness: the evidence dossier's entire claim to
being defensible rests on being able to say exactly which source product,
which model weights, which forcing dataset version and which config
produced a given ranked suspect. A dossier that cannot answer that is an
assertion, not evidence — and the Kerala High Court proceedings against
the MSC ELSA 3 and Wan Hai 503 owners are the live reminder of what this
material is eventually for.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

#: Read files in 1 MiB blocks. Sentinel-1 GRD products are gigabytes;
#: hashing one by slurping it into memory would work on a dev laptop and
#: fail on the demo machine at the worst possible moment.
_HASH_BLOCK_BYTES = 1024 * 1024


def sha256_file(path: str | Path) -> str:
    """SHA-256 of a file's contents, streamed."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(_HASH_BLOCK_BYTES):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_config(config: dict[str, Any]) -> str:
    """Stable hash of a config dict.

    `sort_keys=True` is what makes this stable: without it, two
    semantically identical configs hash differently depending on dict
    insertion order, and every dossier would claim its configuration
    changed between runs when nothing had. `default=str` keeps
    non-JSON-native values (Path, datetime, enum) from raising — they are
    being hashed for identity, not round-tripped.
    """
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_bytes(canonical.encode("utf-8"))


def utc_now() -> datetime:
    """Timezone-aware UTC now.

    Never `datetime.now()` — a naive local timestamp in a provenance
    record is worse than no timestamp, because it looks authoritative
    while being unanchored. Every time in a dossier is UTC.
    """
    return datetime.now(UTC)


class ProvenanceRecord(BaseModel):
    """One pipeline stage's account of what it did.

    Emitted by each module as it runs. Deliberately generic: `inputs` and
    `parameters` are free-form because a SAR preprocessing stage and a
    drift ensemble have nothing structurally in common, and forcing them
    into a shared schema would mean either an unusable lowest common
    denominator or a model that changes every time a module does.

    What is NOT optional is the identifying triple — module, version,
    and when it ran — plus the hashes of whatever went in. A record
    without input hashes cannot support a lineage claim.
    """

    module: str = Field(description="e.g. 'M2.detect', 'M5.drift.backward'")
    version: str = Field(description="module or model version, e.g. 'segformer-b2-oil@1.2'")
    started_at: datetime
    completed_at: datetime | None = None

    #: Hashes of inputs, keyed by role: {"scene": "a3f9...", "weights": "7d41..."}.
    #: Keys are the module's own vocabulary; values are hex digests.
    input_hashes: dict[str, str] = Field(default_factory=dict)

    #: Free-form, must be JSON-serialisable. Everything here lands on the
    #: dossier's provenance page verbatim, so put in what an investigator
    #: would need to reproduce the step, not debug spam.
    parameters: dict[str, Any] = Field(default_factory=dict)

    #: External dataset identifiers and versions: CMEMS product IDs, ERA5
    #: reanalysis version, GEBCO edition, CDSE product ID.
    data_sources: dict[str, str] = Field(default_factory=dict)

    #: Set when the stage produced results from synthetic input. Propagates
    #: to every downstream record and onto every page of the dossier —
    #: see docs/SECURITY.md on labelling synthetic results.
    synthetic: bool = False

    def finish(self) -> ProvenanceRecord:
        """Return a copy marked complete at the current UTC instant."""
        return self.model_copy(update={"completed_at": utc_now()})

    @property
    def duration_seconds(self) -> float | None:
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()


class ProvenanceChain(BaseModel):
    """An ordered set of records for one end-to-end pipeline run.

    `chain_hash` is a hash over the records in order, so a dossier can
    assert that its lineage has not been edited after generation. This is
    the "signed hash chain in a PDF" from docs/PRD.md §14 — deliberately
    not a blockchain, which would do the same job with considerably more
    ceremony and an eye-roll from anyone technical in the room.
    """

    run_id: str
    records: list[ProvenanceRecord] = Field(default_factory=list)

    def add(self, record: ProvenanceRecord) -> None:
        self.records.append(record)

    @property
    def synthetic(self) -> bool:
        """True if ANY stage used synthetic input.

        Deliberately contaminating: one synthetic input makes the whole
        chain synthetic. A run that used a real Sentinel-1 scene but
        synthetic AIS produced a synthetic attribution, and labelling it
        anything else would overstate what it demonstrates.
        """
        return any(r.synthetic for r in self.records)

    def chain_hash(self) -> str:
        payload = [r.model_dump(mode="json") for r in self.records]
        return sha256_config({"run_id": self.run_id, "records": payload})


def collect_input_hashes(paths: Iterable[str | Path]) -> dict[str, str]:
    """Hash several files, keyed by filename.

    Convenience for the common case of a stage consuming a handful of
    named artefacts. Uses the basename as the key, so callers with
    same-named files in different directories should build the dict
    themselves rather than silently losing one to a key collision.
    """
    result: dict[str, str] = {}
    for path in paths:
        p = Path(path)
        result[p.name] = sha256_file(p)
    return result
