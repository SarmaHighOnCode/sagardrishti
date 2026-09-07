"""Domain types crossing module boundaries.

## Why these are not the same as the API's schemas

`services/api/app/schemas.py` holds the *wire* types — the shapes
docs/api/API_CONTRACT.md freezes on 15 October. These are the *domain*
types the pipeline passes between M1–M7. They overlap heavily today and
it is fair to ask why both exist.

The answer is the freeze date. After 15 October the wire shapes cannot
change without a version bump and the integration lead's sign-off,
because a frontend depends on them. The pipeline's internal types must
stay free to change — M3 will learn new slick attributes, M6 will gain
scoring factors — and coupling those two lifecycles would mean either
the contract thaws or the pipeline freezes. Neither is acceptable.

The cost is a mapping layer at the API boundary. That is the intended
trade, and it is small: the mapping is mechanical and testable, and it
is the place to absorb a rename rather than propagating it to the
console.

**The one thing to avoid:** letting the two drift apart *silently* on
fields that are supposed to mean the same thing. That already nearly
happened once — the API's BaselineGapProfile independently invented
`typical_gap_minutes_p50` against a database column called
`median_gap_seconds`, caught only because someone read the merged schema
before writing fixtures. When you change a field here that has a wire
counterpart, change both, or write down why they now differ.

## Uncertainty pairing

Inferred quantities carry their interval in the same model, both fields
required with no default, so one cannot be dropped while keeping the
other. Product principle 2, enforced by the type system rather than by
remembering. See `SlickAgeEstimate` and `ReleaseTimeEstimate`.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .geo import LonLat


class Classification(StrEnum):
    OIL = "oil"
    LOOK_ALIKE = "look_alike"


class ThicknessClass(StrEnum):
    """Relative only. C-band SAR cannot retrieve absolute film thickness —
    docs/PRD.md §4.5 puts volume estimation explicitly out of scope, and
    these two classes are the most the physics supports."""

    SHEEN = "sheen"
    THICK_FILM = "thick_film"


class DriftMode(StrEnum):
    #: Weathering OFF. Evaporation and emulsification are irreversible;
    #: running them backwards is physically meaningless (PRD §7.7).
    BACKWARD = "backward"
    FORWARD = "forward"
    PER_VESSEL = "per_vessel"


class FactorConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataQuality(StrEnum):
    OK = "ok"
    #: Marked, never deleted. Excluded from the confident evidence set,
    #: and must not shift a suspicion score in EITHER direction — a vessel
    #: never becomes a suspect because its transponder is broken.
    UNRELIABLE = "unreliable"


# --------------------------------------------------------------------------
# Uncertainty-bearing estimates
# --------------------------------------------------------------------------


class Interval(BaseModel):
    """A closed interval. `lo <= hi` is validated, not assumed."""

    lo: float
    hi: float

    @model_validator(mode="after")
    def _ordered(self) -> Interval:
        if self.lo > self.hi:
            raise ValueError(f"interval lo ({self.lo}) must not exceed hi ({self.hi})")
        return self

    def contains(self, value: float) -> bool:
        return self.lo <= value <= self.hi

    @property
    def width(self) -> float:
        return self.hi - self.lo


class SlickAgeEstimate(BaseModel):
    """Slick age, INFERRED — never measured.

    Age is not recoverable from a single SAR scene (PRD §2.5): contrast
    correlates with age but is confounded by wind, incidence angle, oil
    type and discharge volume. What this represents is the release time
    that best explains the observed slick given a candidate vessel's
    track and the drift field, per ADR 0001. The interval comes from the
    ensemble spread, and reporting the value without it would be exactly
    the bare point estimate the product principles forbid.
    """

    hours: float
    ci: Interval


class ReleaseTimeEstimate(BaseModel):
    """Inferred discharge time, with its uncertainty in minutes."""

    at: datetime
    ci_minutes: float


# --------------------------------------------------------------------------
# Scenes and detections
# --------------------------------------------------------------------------


class Scene(BaseModel):
    id: str
    sensor: str
    acquired_at: datetime
    footprint: list[LonLat]
    product_hash: str

    #: Ground sample distance after M1 resampling. Fixed at 40 m/px
    #: repo-wide (ADR 0002) — carried explicitly rather than assumed,
    #: because a silent GSD mismatch between training and inference is
    #: the failure mode that looks like domain shift and isn't.
    gsd_metres: float = 40.0


class Penalty(BaseModel):
    """One Stage C context check that reduced a detection's confidence.

    `reason` is rendered directly to the analyst; `evidence` is the
    machine-readable backing the dossier cites. Both are required
    together — a penalty that cannot explain itself is not usable in the
    rejection panel, which is the single cheapest credibility feature in
    the product (docs/DESIGN_SYSTEM.md §6.3).
    """

    check: str
    delta: float
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class SlickAttributes(BaseModel):
    """M3 output — geometric and radiometric characterisation."""

    area_km2: float
    perimeter_km: float
    major_axis_bearing_deg: float
    eccentricity: float
    complexity_index: float = Field(
        description="P^2 / 4·pi·A. 1.0 for a circle, higher for ragged or elongated shapes"
    )
    damping_ratio_db: float
    edge_sharpness: float
    thickness_class: ThicknessClass


class SlickPolygon(BaseModel):
    """A detected slick: geometry plus how much we believe it."""

    id: str
    scene_id: str
    boundary: list[LonLat]
    classification: Classification

    #: Post-Stage-C value, and the raw pre-filter value it came from.
    #: Both kept: the UI strikes through the raw figure rather than
    #: hiding that the model was initially more confident.
    confidence: float
    confidence_raw: float
    penalties: list[Penalty] = Field(default_factory=list)
    attributes: SlickAttributes | None = None

    @model_validator(mode="after")
    def _penalties_explain_the_drop(self) -> SlickPolygon:
        """A confidence drop must be accounted for by the penalty log.

        Not a numeric reconciliation — Stage C combines penalties
        non-additively — but a structural one: if confidence fell, at
        least one penalty must say why. A silent drop is unexplainable to
        an analyst and would be indefensible in a dossier.
        """
        if self.confidence < self.confidence_raw and not self.penalties:
            raise ValueError(
                f"confidence dropped {self.confidence_raw} -> {self.confidence} "
                "with an empty penalty log: every reduction must be attributable"
            )
        return self


# --------------------------------------------------------------------------
# Attribution
# --------------------------------------------------------------------------


class ScoringFactor(BaseModel):
    """One weighted term in the log-odds suspect score.

    `contribution` is weight × value, stored rather than recomputed so
    the UI's per-factor bars show the arithmetic that actually ran. It
    may be NEGATIVE — exculpatory factors are first-class here and are
    never filtered out (docs/SCORING_MODEL.md §7).
    """

    name: str
    value: float
    weight: float
    contribution: float
    confidence: FactorConfidence = FactorConfidence.HIGH
    #: Required where the bare value would mislead — notably
    #: ais_gap_anomaly, where "0.62" means nothing without knowing it was
    #: measured against this vessel's own baseline.
    note: str | None = None


class DataQualitySummary(BaseModel):
    records_used: int
    records_excluded: int
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)


class Suspect(BaseModel):
    """A ranked candidate vessel. Never an accusation.

    The system outputs calibrated probabilities with per-factor
    explanations. `posterior` is a probability that this vessel is the
    source, not a verdict, and `calibrated` records whether it has been
    through Platt/isotonic calibration — an uncalibrated score is
    ordinal only and must not be presented as a probability.
    """

    detection_id: str
    mmsi: str
    rank: int
    posterior: float
    calibrated: bool
    imo: str | None = None
    vessel_name: str | None = None
    vessel_type: str | None = None

    release: ReleaseTimeEstimate
    slick_age: SlickAgeEstimate

    factors: list[ScoringFactor]
    data_quality: DataQualitySummary

    @model_validator(mode="after")
    def _posterior_is_a_probability(self) -> Suspect:
        if not 0.0 <= self.posterior <= 1.0:
            raise ValueError(f"posterior must be a probability in [0,1], got {self.posterior}")
        return self


class DriftRun(BaseModel):
    """One ensemble run's configuration and forcing lineage.

    A single deterministic run is not a result (PRD §7.7) — the spread
    across members IS the uncertainty estimate, so `ensemble_members` is
    required and a value of 1 should be treated as a diagnostic run, not
    something to report an origin from.
    """

    id: str
    detection_id: str
    mode: DriftMode
    ensemble_members: int
    started_at: datetime
    completed_at: datetime | None = None
    #: CMEMS/ERA5/GEBCO product IDs and versions — straight onto the
    #: dossier's provenance page.
    forcing_versions: dict[str, str] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _weathering_off_when_backward(self) -> DriftRun:
        """Backward runs must not weather.

        Evaporation and emulsification are irreversible; running them in
        reverse un-evaporates oil and produces confident nonsense. Cheap
        to assert here, and a genuinely easy mistake to make when the
        same config dict is reused between forward and backward runs.
        """
        if self.mode is DriftMode.BACKWARD and self.config.get("weathering") is True:
            raise ValueError(
                "backward drift runs must have weathering disabled: evaporation and "
                "emulsification are irreversible (PRD §7.7)"
            )
        return self
