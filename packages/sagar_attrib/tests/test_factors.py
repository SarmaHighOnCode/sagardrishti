from __future__ import annotations

from sagar_attrib import factors as f


class TestF1DriftConsistency:
    def test_perfect_hit_and_coverage_scores_one(self):
        assert f.f1_drift_consistency(hit=1.0, coverage=1.0).value == 1.0

    def test_zero_hit_and_coverage_scores_zero_without_dividing_by_zero(self):
        assert f.f1_drift_consistency(hit=0.0, coverage=0.0).value == 0.0

    def test_tiny_plume_in_a_huge_slick_is_penalised(self):
        """High hit, low coverage — the F-measure must not reward this."""
        factor = f.f1_drift_consistency(hit=1.0, coverage=0.05)
        assert factor.value < 0.2

    def test_smeared_plume_across_the_whole_region_is_penalised(self):
        """High coverage, low hit — the other failure mode."""
        factor = f.f1_drift_consistency(hit=0.05, coverage=1.0)
        assert factor.value < 0.2

    def test_weight_matches_the_documented_prior(self):
        assert f.f1_drift_consistency(hit=0.5, coverage=0.5).weight == 2.5


class TestF2CourseAlignment:
    def test_perfectly_aligned_scores_one(self):
        factor = f.f2_course_alignment(
            slick_bearing_deg=90, vessel_cog_deg=90, slick_eccentricity=0.9
        )
        assert factor is not None
        assert factor.value == 1.0

    def test_perpendicular_scores_zero(self):
        factor = f.f2_course_alignment(
            slick_bearing_deg=0, vessel_cog_deg=90, slick_eccentricity=0.9
        )
        assert factor is not None
        assert abs(factor.value) < 1e-9

    def test_opposite_bearing_still_counts_as_aligned(self):
        """A slick's major axis has no inherent direction — 180 deg off
        is the SAME line, not a mismatch."""
        factor = f.f2_course_alignment(
            slick_bearing_deg=90, vessel_cog_deg=270, slick_eccentricity=0.9
        )
        assert factor is not None
        assert factor.value == 1.0

    def test_dropped_not_zeroed_for_a_nearly_round_slick(self):
        """docs/SCORING_MODEL.md f2's guard — None, not a ScoringFactor
        with value 0, because a bearing for a round slick is noise, not
        evidence of misalignment."""
        factor = f.f2_course_alignment(
            slick_bearing_deg=90, vessel_cog_deg=90, slick_eccentricity=0.1
        )
        assert factor is None


class TestF3SpeedAnomaly:
    def test_at_median_speed_scores_zero(self):
        assert f.f3_speed_anomaly(sog_at_release_knots=10, sog_median_knots=10).value == 0.0

    def test_slower_than_median_scores_positive(self):
        assert f.f3_speed_anomaly(sog_at_release_knots=4, sog_median_knots=10).value > 0

    def test_faster_than_median_never_scores_negative(self):
        """docs/SCORING_MODEL.md f3: one-sided — going faster is not
        evidence of innocence."""
        assert f.f3_speed_anomaly(sog_at_release_knots=20, sog_median_knots=10).value == 0.0

    def test_zero_median_does_not_raise_a_division_error(self):
        assert f.f3_speed_anomaly(sog_at_release_knots=5, sog_median_knots=0).value == 0.0


class TestF5CourseChange:
    def test_no_change_scores_zero(self):
        assert f.f5_course_change(0).value == 0.0

    def test_large_change_saturates_at_one(self):
        assert f.f5_course_change(180).value == 1.0

    def test_negative_angle_uses_magnitude(self):
        assert f.f5_course_change(-45).value == f.f5_course_change(45).value


class TestF6NightTimeRelease:
    def test_night_scores_one(self):
        assert f.f6_night_time_release(True).value == 1.0

    def test_day_scores_zero(self):
        assert f.f6_night_time_release(False).value == 0.0


class TestF7OffLaneDistance:
    def test_squarely_in_lane_is_mildly_exculpatory(self):
        """docs/SCORING_MODEL.md f7: negative, not merely zero."""
        assert f.f7_off_lane_distance(0).value < 0

    def test_far_off_lane_saturates_at_one(self):
        assert f.f7_off_lane_distance(1000).value == 1.0

    def test_value_never_exceeds_the_documented_range(self):
        for km in (-10, 0, 5, 20, 50, 10_000):
            value = f.f7_off_lane_distance(km).value
            assert -0.5 <= value <= 1.0


class TestF8VesselTypePrior:
    def test_missing_type_is_dropped_not_defaulted(self):
        assert f.f8_vessel_type_prior(None) is None
        assert f.f8_vessel_type_prior("") is None

    def test_tanker_scores_highest_among_the_documented_ordering(self):
        tanker = f.f8_vessel_type_prior("tanker").value
        bulk = f.f8_vessel_type_prior("bulk_carrier").value
        container = f.f8_vessel_type_prior("container").value
        cargo = f.f8_vessel_type_prior("general_cargo").value
        fishing = f.f8_vessel_type_prior("fishing").value
        # docs/SCORING_MODEL.md f8: "tanker > bulk carrier > container >
        # general cargo > fishing > other"
        assert tanker > bulk > container > cargo > fishing

    def test_an_unrecognised_but_present_type_falls_back_to_other_not_dropped(self):
        """The guard is for ABSENT data, not an unfamiliar value."""
        factor = f.f8_vessel_type_prior("some_new_iso_category")
        assert factor is not None
        assert factor.value == f.f8_vessel_type_prior("other").value

    def test_is_case_insensitive(self):
        assert f.f8_vessel_type_prior("TANKER").value == f.f8_vessel_type_prior("tanker").value


class TestF9ContextualProximity:
    def test_far_from_everything_scores_zero(self):
        factor = f.f9_contextual_proximity(
            distance_to_port_km=1000, distance_to_platform_km=1000, in_eco_zone=False
        )
        assert factor.value == 0.0

    def test_in_eco_zone_alone_scores_one_even_if_far_from_port_and_platform(self):
        factor = f.f9_contextual_proximity(
            distance_to_port_km=1000, distance_to_platform_km=1000, in_eco_zone=True
        )
        assert factor.value == 1.0

    def test_components_do_not_stack_additively(self):
        """Close to both port AND platform should not exceed 1.0 — the
        composite is a max, not a sum, of non-additive reasons."""
        factor = f.f9_contextual_proximity(
            distance_to_port_km=0, distance_to_platform_km=0, in_eco_zone=False
        )
        assert factor.value == 1.0


def test_every_factor_has_a_positive_weight_matching_docs_scoring_model():
    """docs/SCORING_MODEL.md §3's weight table, checked against the
    values actually wired into each function's ScoringFactor."""
    expected = {
        "drift_consistency": 2.5,
        "course_alignment": 1.4,
        "speed_anomaly": 1.1,
        "course_change": 0.6,
        "night_time_release": 0.5,
        "off_lane_distance": 0.8,
        "vessel_type_prior": 0.7,
        "contextual_proximity": 0.4,
    }
    got = {
        "drift_consistency": f.f1_drift_consistency(0.5, 0.5).weight,
        "course_alignment": f.f2_course_alignment(0, 0, 0.9).weight,
        "speed_anomaly": f.f3_speed_anomaly(5, 10).weight,
        "course_change": f.f5_course_change(10).weight,
        "night_time_release": f.f6_night_time_release(True).weight,
        "off_lane_distance": f.f7_off_lane_distance(5).weight,
        "vessel_type_prior": f.f8_vessel_type_prior("tanker").weight,
        "contextual_proximity": f.f9_contextual_proximity(5, 5, False).weight,
    }
    assert got == expected
