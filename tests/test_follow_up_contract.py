from talent_intel_crm.workflows.follow_up import DEFAULT_FOLLOW_UP_DELAYS_SECONDS, _cadence_delays


def test_follow_up_defaults_to_d5_and_d7() -> None:
    assert _cadence_delays(None) == DEFAULT_FOLLOW_UP_DELAYS_SECONDS


def test_follow_up_validation_allows_zero_delay_smoke_runs() -> None:
    assert _cadence_delays([0, "7", -1, True, "bad"]) == [0, 7, 0]
