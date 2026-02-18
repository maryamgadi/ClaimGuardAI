from claimguard.scoring import compute_score


def test_compute_score_no_anomalies():
    assert compute_score([]) == 1.0


def test_compute_score_with_anomalies():
    assert compute_score(["a"]) == 0.9
    assert compute_score(["a"] * 20) == 0.0
