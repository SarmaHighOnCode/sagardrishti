"""Domain type invariants and provenance capture.

The type tests here are not about Pydantic working — they are about the
handful of rules the project's credibility rests on being impossible to
violate by accident: uncertainty always paired, confidence drops always
explained, backward drift never weathering, synthetic labelling never
lost.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sagar_core.provenance import (
    ProvenanceChain,
    ProvenanceRecord,
    sha256_bytes,
    sha256_config,
    utc_now,
)
from sagar_core.types import (
    Classification,
    DataQualitySummary,
    DriftMode,
    DriftRun,
    Interval,
    Penalty,
    ReleaseTimeEstimate,
    ScoringFactor,
    SlickAgeEstimate,
    SlickPolygon,
    Suspect,
)

NOW = datetime(2026, 5, 25, 6, 40, tzinfo=UTC)


class TestInterval:
    def test_rejects_inverted_bounds(self):
        with pytest.raises(ValidationError):
            Interval(lo=8.8, hi=5.9)

    def test_degenerate_interval_is_allowed(self):
        # lo == hi is a legitimate zero-width interval, not an error.
        assert Interval(lo=7.3, hi=7.3).width == 0.0

    def test_contains_and_width(self):
        iv = Interval(lo=5.9, hi=8.8)
        assert iv.contains(7.3)
        assert not iv.contains(9.0)
        assert iv.width == pytest.approx(2.9)


class TestUncertaintyIsAlwaysPaired:
    """Product principle 2, enforced by construction."""

    def test_slick_age_requires_its_interval(self):
        with pytest.raises(ValidationError):
            SlickAgeEstimate(hours=7.3)  # type: ignore[call-arg]

    def test_release_time_requires_its_interval(self):
        with pytest.raises(ValidationError):
            ReleaseTimeEstimate(at=NOW)  # type: ignore[call-arg]

    def test_valid_pair_constructs(self):
        age = SlickAgeEstimate(hours=7.3, ci=Interval(lo=5.9, hi=8.8))
        assert age.ci.contains(age.hours)


def _slick(**overrides) -> dict:
    base = dict(
        id="det_1",
        scene_id="S1C_TEST",
        boundary=[(75.4, 9.8), (75.6, 9.7), (75.5, 9.6)],
        classification=Classification.OIL,
        confidence=0.81,
        confidence_raw=0.81,
        penalties=[],
    )
    base.update(overrides)
    return base


class TestConfidenceDropsMustBeExplained:
    def test_unexplained_drop_is_rejected(self):
        with pytest.raises(ValidationError, match="attributable"):
            SlickPolygon(**_slick(confidence=0.19, confidence_raw=0.62, penalties=[]))

    def test_explained_drop_is_accepted(self):
        slick = SlickPolygon(
            **_slick(
                confidence=0.19,
                confidence_raw=0.62,
                classification=Classification.LOOK_ALIKE,
                penalties=[
                    Penalty(
                        check="wind_window",
                        delta=-0.28,
                        reason="wind speed 1.6 m/s below 2-12 m/s detection window",
                        evidence={"wind_ms": 1.6},
                    )
                ],
            )
        )
        assert slick.penalties[0].reason

    def test_no_drop_needs_no_penalties(self):
        assert SlickPolygon(**_slick()).penalties == []


class TestSuspect:
    def _suspect(self, **overrides) -> dict:
        base = dict(
            detection_id="det_1",
            mmsi="419001234",
            rank=1,
            posterior=0.71,
            calibrated=True,
            release=ReleaseTimeEstimate(at=NOW, ci_minutes=50),
            slick_age=SlickAgeEstimate(hours=7.3, ci=Interval(lo=5.9, hi=8.8)),
            factors=[
                ScoringFactor(name="drift_consistency", value=0.81, weight=2.5, contribution=2.14)
            ],
            data_quality=DataQualitySummary(records_used=412, records_excluded=7),
        )
        base.update(overrides)
        return base

    def test_constructs(self):
        assert Suspect(**self._suspect()).rank == 1

    def test_posterior_must_be_a_probability(self):
        with pytest.raises(ValidationError, match="probability"):
            Suspect(**self._suspect(posterior=1.4))

    def test_negative_contribution_is_first_class(self):
        """Exculpatory factors are ordinary data, never filtered out."""
        s = Suspect(
            **self._suspect(
                factors=[
                    ScoringFactor(
                        name="off_lane_distance", value=-0.17, weight=0.8, contribution=-0.22
                    )
                ]
            )
        )
        assert s.factors[0].contribution < 0


class TestDriftRun:
    def _run(self, **overrides) -> dict:
        base = dict(
            id="drift_1",
            detection_id="det_1",
            mode=DriftMode.BACKWARD,
            ensemble_members=100,
            started_at=NOW,
            config={},
        )
        base.update(overrides)
        return base

    def test_backward_run_rejects_weathering(self):
        """Irreversible processes must not run in reverse (PRD 7.7)."""
        with pytest.raises(ValidationError, match="weathering"):
            DriftRun(**self._run(config={"weathering": True}))

    def test_backward_run_without_weathering_is_fine(self):
        assert DriftRun(**self._run(config={"weathering": False})).mode is DriftMode.BACKWARD

    def test_forward_run_may_weather(self):
        run = DriftRun(**self._run(mode=DriftMode.FORWARD, config={"weathering": True}))
        assert run.mode is DriftMode.FORWARD


class TestProvenance:
    def test_config_hash_is_order_independent(self):
        """Two semantically identical configs must hash identically, or
        every dossier claims its configuration changed when it didn't."""
        a = sha256_config({"members": 100, "mode": "backward"})
        b = sha256_config({"mode": "backward", "members": 100})
        assert a == b

    def test_config_hash_changes_when_a_value_changes(self):
        a = sha256_config({"members": 100})
        b = sha256_config({"members": 101})
        assert a != b

    def test_config_hash_handles_non_json_values(self):
        from pathlib import Path

        # Must not raise on Path/datetime — they are hashed for identity.
        assert sha256_config({"root": Path("/data"), "at": NOW})

    def test_known_sha256(self):
        # Anchors the digest against a published value, guarding against
        # someone "optimising" this into a different (non-SHA256) hash.
        assert sha256_bytes(b"abc").startswith("ba7816bf8f01cfea")

    def test_record_finish_sets_completion_and_duration(self):
        rec = ProvenanceRecord(module="M2.detect", version="v1", started_at=utc_now())
        assert rec.duration_seconds is None
        done = rec.finish()
        assert done.completed_at is not None
        assert done.duration_seconds is not None and done.duration_seconds >= 0

    def test_utc_now_is_timezone_aware(self):
        """A naive timestamp in a provenance record looks authoritative
        while being unanchored — worse than none."""
        assert utc_now().tzinfo is not None

    def test_synthetic_flag_contaminates_the_whole_chain(self):
        chain = ProvenanceChain(run_id="run_1")
        chain.add(ProvenanceRecord(module="M1", version="v1", started_at=NOW, synthetic=False))
        assert chain.synthetic is False
        chain.add(
            ProvenanceRecord(
                module="M6", version="v1", started_at=NOW + timedelta(minutes=5), synthetic=True
            )
        )
        # One synthetic input makes the whole run synthetic. A real scene
        # plus synthetic AIS produced a synthetic attribution.
        assert chain.synthetic is True

    def test_chain_hash_detects_tampering(self):
        chain = ProvenanceChain(run_id="run_1")
        chain.add(ProvenanceRecord(module="M1", version="v1", started_at=NOW))
        before = chain.chain_hash()

        chain.records[0].parameters["gsd_metres"] = 10.0  # someone edits history
        assert chain.chain_hash() != before

    def test_chain_hash_is_stable_for_unchanged_content(self):
        chain = ProvenanceChain(run_id="run_1")
        chain.add(ProvenanceRecord(module="M1", version="v1", started_at=NOW))
        assert chain.chain_hash() == chain.chain_hash()

    def test_record_is_json_serialisable(self):
        """Records land in a dossier and a JSONB column; anything that
        cannot serialise cleanly breaks both."""
        rec = ProvenanceRecord(
            module="M5.drift.backward",
            version="opendrift-1.11",
            started_at=NOW,
            input_hashes={"scene": "a3f9"},
            parameters={"members": 100},
            data_sources={"currents": "CMEMS GLOBAL_ANALYSISFORECAST_PHY_001_024"},
        )
        assert json.loads(rec.model_dump_json())["module"] == "M5.drift.backward"


class TestSettingsRedaction:
    def test_secrets_are_not_in_repr(self):
        from sagar_core.config import Settings

        s = Settings(aisstream_api_key="super-secret-value", cdse_client_secret="also-secret")
        text = repr(s)
        assert "super-secret-value" not in text
        assert "also-secret" not in text
        assert "<set>" in text

    def test_secrets_are_not_in_snapshot(self):
        """A snapshot gets hashed into provenance and can reach a dossier."""
        from sagar_core.config import Settings

        s = Settings(aisstream_api_key="super-secret-value")
        snap = s.snapshot()
        assert "aisstream_api_key" not in snap
        assert "super-secret-value" not in json.dumps(snap)
