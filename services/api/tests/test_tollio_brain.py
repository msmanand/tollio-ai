from app.services.tollio_brain import (
    BrainProfile,
    BrainRoad,
    OFFICIAL_ROADS,
    analyzeEntry,
    analyzeExit,
    entryVScore,
    exitVScore,
    getPrice,
    optimizeTrip,
    projectAnnualSaving,
    serviceRoadGasCost,
    unusedAhead,
    vScore,
    wastedBehind,
)


def _matrix(entries):
    return {
        (min(a, b), max(a, b)): value
        for (a, b), value in entries.items()
    }


def _score_road():
    return BrainRoad(
        id=0,
        short="TEST",
        name="Test Tollway",
        exits=[f"Exit {idx}" for idx in range(16)],
        matrix=_matrix(
            {
                (5, 15): 10.0,
                (6, 15): 10.0,
                (7, 15): 10.0,
                (3, 9): 8.0,
                (3, 10): 8.0,
                (3, 11): 8.0,
            }
        ),
    )


def _analysis_road():
    return BrainRoad(
        id=0,
        short="TEST",
        name="Test Tollway",
        exits=[f"Exit {idx}" for idx in range(8)],
        matrix=_matrix(
            {
                (2, 7): 5.0,
                (3, 7): 4.5,
                (4, 7): 3.0,
                (3, 6): 4.0,
                (2, 6): 4.5,
                (2, 5): 3.0,
                (3, 5): 2.5,
            }
        ),
    )


def test_entry_vscore_matches_brain_example():
    assert entryVScore(_score_road(), 7, 15, "tolltag") == 80


def test_exit_vscore_matches_brain_example():
    assert exitVScore(_score_road(), 3, 9, "tolltag") == 75


def test_vscore_returns_minimum():
    road = _score_road()
    assert vScore(road, 7, 15, "tolltag") == min(
        entryVScore(road, 7, 15, "tolltag"),
        exitVScore(road, 7, 15, "tolltag"),
    )


def test_wasted_behind_works():
    assert wastedBehind(_score_road(), 7, 15, "tolltag") == 2


def test_unused_ahead_works():
    assert unusedAhead(_score_road(), 3, 9, "tolltag") == 2


def test_analyze_entry_finds_first_better_entry():
    analysis = analyzeEntry(0, 2, 7, BrainProfile(mpg=30, gas_price=3.0), [_analysis_road()])

    assert analysis.suggestion is not None
    assert analysis.suggestion.exit_idx == 3
    assert analysis.suggestion.saving == 0.5
    assert analysis.suggestion.svc_mins == 2


def test_analyze_exit_finds_first_better_exit():
    analysis = analyzeExit(0, 2, 7, BrainProfile(mpg=30, gas_price=3.0), [_analysis_road()])

    assert analysis.suggestion is not None
    assert analysis.suggestion.exit_idx == 6
    assert analysis.suggestion.saving == 0.5
    assert analysis.suggestion.svc_mins == 2


def test_net_savings_calculation_is_correct():
    result = optimizeTrip(0, 2, 0, 7, BrainProfile(mpg=30, gas_price=3.0), [_analysis_road()])[0]

    assert result.natural_total == 5.0
    assert result.total_price == 4.0
    assert result.toll_saved == 1.0
    assert result.gas_cost == 0.18
    assert result.net_saving == 0.82


def test_ev_gas_cost_is_zero():
    assert serviceRoadGasCost(12, 30, 3.5, "ev") == 0


def test_optimize_trip_ranks_best_result():
    result = optimizeTrip(0, 2, 0, 7, BrainProfile(mpg=30, gas_price=3.0), [_analysis_road()])[0]

    assert result.is_best is True
    assert result.avg_value_score >= 0


def test_no_invented_toll_values_for_unmapped_official_relationship():
    assert getPrice(OFFICIAL_ROADS[0], 1, 2, "tolltag") is None


def test_project_annual_saving():
    assert projectAnnualSaving(1.25) == 550.0
