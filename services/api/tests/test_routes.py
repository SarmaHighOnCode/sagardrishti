"""Exercises every endpoint in docs/api/API_CONTRACT.md against the
running app. For each: does it return the documented shape, and for the
not-yet-built pipeline stages, does it fail HONESTLY (501 with a clear
reason) rather than fabricating a result or silently succeeding.
"""

from __future__ import annotations

from app.fixtures import DETECTION_LOOKALIKE, DETECTION_OIL, SCENE

PROBLEM_JSON = "application/problem+json"


# --------------------------------------------------------------------
# Scenes
# --------------------------------------------------------------------


def test_list_scenes(client):
    r = client.get("/api/v1/scenes")
    assert r.status_code == 200
    body = r.json()
    assert body["items"][0]["id"] == SCENE.id


def test_get_scene(client):
    r = client.get(f"/api/v1/scenes/{SCENE.id}")
    assert r.status_code == 200
    assert r.json()["sensor"] == "Sentinel-1C"


def test_get_scene_unknown_is_problem_json_404(client):
    r = client.get("/api/v1/scenes/does-not-exist")
    assert r.status_code == 404
    assert r.headers["content-type"] == PROBLEM_JSON
    assert r.json()["status"] == 404


def test_analyse_scene_is_honestly_not_implemented(client):
    r = client.post(f"/api/v1/scenes/{SCENE.id}/analyse")
    assert r.status_code == 501
    assert r.headers["content-type"] == PROBLEM_JSON
    # Must not look like a real 202 - see errors.not_implemented's docstring.
    assert "job" in r.json()["detail"].lower()


# --------------------------------------------------------------------
# Detections
# --------------------------------------------------------------------


def test_list_detections_unfiltered_returns_both_fixtures(client):
    r = client.get("/api/v1/detections")
    assert r.status_code == 200
    ids = {d["id"] for d in r.json()["items"]}
    assert ids == {DETECTION_OIL.id, DETECTION_LOOKALIKE.id}


def test_list_detections_min_confidence_filters_out_the_lookalike(client):
    r = client.get("/api/v1/detections", params={"min_confidence": 0.5})
    ids = {d["id"] for d in r.json()["items"]}
    assert ids == {DETECTION_OIL.id}


def test_get_detection_rejection_reasoning_matches_the_contract_example(client):
    """This is the exact worked example from API_CONTRACT.md's
    "GET /detections/{id}" section - the 1:50 demo beat. If this test ever
    fails, the console's rejection panel and the contract doc have
    diverged from what the API actually serves."""
    r = client.get(f"/api/v1/detections/{DETECTION_LOOKALIKE.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["confidence"] == 0.19
    assert body["confidence_raw"] == 0.62
    assert body["classification"] == "look_alike"
    reasons = [p["reason"] for p in body["penalties"]]
    assert any("wind" in r.lower() for r in reasons)
    assert any("chlorophyll" in r.lower() for r in reasons)
    assert any("dark formation" in r.lower() for r in reasons)


def test_get_detection_unknown_is_404(client):
    r = client.get("/api/v1/detections/does-not-exist")
    assert r.status_code == 404


def test_suspects_include_the_negative_contribution(client):
    """SCORING_MODEL.md §7: every factor is listed, including those
    arguing for innocence. If a future change filtered negative
    contributions out "to keep the UI clean", this test catches it."""
    r = client.get(f"/api/v1/detections/{DETECTION_OIL.id}/suspects")
    assert r.status_code == 200
    suspects = r.json()
    top = suspects[0]
    assert top["rank"] == 1
    negative = [f for f in top["factors"] if f["contribution"] < 0]
    assert negative, "expected at least one exculpatory factor in the fixture"


def test_suspects_for_unknown_detection_is_404(client):
    r = client.get("/api/v1/detections/does-not-exist/suspects")
    assert r.status_code == 404


def test_hindcast_is_honestly_not_implemented(client):
    r = client.get(f"/api/v1/detections/{DETECTION_OIL.id}/hindcast")
    assert r.status_code == 501
    assert r.headers["content-type"] == PROBLEM_JSON


def test_forecast_is_honestly_not_implemented(client):
    r = client.get(f"/api/v1/detections/{DETECTION_OIL.id}/forecast")
    assert r.status_code == 501


def test_audit_trail_shows_the_214_to_7_cascade(client):
    r = client.get(f"/api/v1/detections/{DETECTION_OIL.id}/audit")
    assert r.status_code == 200
    body = r.json()
    assert body["final_candidate_count"] == 7
    assert body["stages"][0]["before"] == 214


def test_evidence_is_honestly_not_implemented(client):
    r = client.post(f"/api/v1/detections/{DETECTION_OIL.id}/evidence")
    assert r.status_code == 501


# --------------------------------------------------------------------
# AIS and ships
# --------------------------------------------------------------------


def test_list_ais_tracks(client):
    r = client.get("/api/v1/ais/tracks")
    assert r.status_code == 200
    assert r.json()["items"][0]["mmsi"] == "419001234"


def test_ais_track_points_are_time_ordered(client):
    r = client.get("/api/v1/ais/tracks", params={"mmsi": "419001234"})
    points = r.json()["items"][0]["points"]
    times = [p["time_utc"] for p in points]
    assert times == sorted(times)
    assert len(set(times)) == len(times), "track points must not share a timestamp"


def test_get_vessel_with_sufficient_history(client):
    r = client.get("/api/v1/ais/vessels/419001234")
    assert r.status_code == 200
    profile = r.json()["baseline_gap_profile"]
    assert profile["has_sufficient_history"] is True


def test_get_vessel_with_insufficient_history_is_flagged_not_defaulted(client):
    """SCORING_MODEL.md §5: an unknown vessel is unknown, never silently
    treated as average. has_sufficient_history=False is how the UI knows
    to mark the factor low-confidence rather than trust it at face value."""
    r = client.get("/api/v1/ais/vessels/563889000")
    profile = r.json()["baseline_gap_profile"]
    assert profile["has_sufficient_history"] is False


def test_get_vessel_unknown_mmsi_is_404(client):
    r = client.get("/api/v1/ais/vessels/000000000")
    assert r.status_code == 404


def test_list_ships_includes_the_dark_vessel(client):
    r = client.get("/api/v1/ships")
    assert r.status_code == 200
    dark = [s for s in r.json()["items"] if s["dark_vessel"]]
    assert len(dark) == 1
    assert dark[0]["ais_match"] is None


def test_dark_vessel_size_bucket_is_present_but_not_a_filter(client):
    """PRD §7.6: size_bucket is a soft flag, never a hard filter. The dark
    small vessel must still appear in the unfiltered list."""
    r = client.get("/api/v1/ships")
    ids = {s["id"] for s in r.json()["items"]}
    assert "shp_3" in ids  # the dark, small, AIS-exempt-likely vessel


def test_get_ship_unknown_is_404(client):
    r = client.get("/api/v1/ships/does-not-exist")
    assert r.status_code == 404


# --------------------------------------------------------------------
# Jobs - no store exists, so every lookup is a genuine 404
# --------------------------------------------------------------------


def test_get_job_is_404_not_501(client):
    """Distinct from the pipeline endpoints above: this endpoint IS
    implemented, its store is just always empty right now, so a 404 is
    the honest answer rather than a 501."""
    r = client.get("/api/v1/jobs/job_does_not_exist")
    assert r.status_code == 404


def test_get_job_events_is_404(client):
    r = client.get("/api/v1/jobs/job_does_not_exist/events")
    assert r.status_code == 404


# --------------------------------------------------------------------
# Cross-cutting: every error response is RFC 7807, not FastAPI's default
# --------------------------------------------------------------------


def test_every_404_is_problem_json(client):
    for path in (
        "/api/v1/scenes/nope",
        "/api/v1/detections/nope",
        "/api/v1/detections/nope/suspects",
        "/api/v1/ais/vessels/000000000",
        "/api/v1/ships/nope",
        "/api/v1/jobs/nope",
    ):
        r = client.get(path)
        assert r.status_code == 404, path
        assert r.headers["content-type"] == PROBLEM_JSON, path
        body = r.json()
        assert body["title"] == "Not Found"
        assert "detail" in body
