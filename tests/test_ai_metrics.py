from sum_backend.ai_metrics import summarize_latencies


def test_stage_summary_has_count_mean_and_approximate_percentiles():
    result = summarize_latencies([100, 200, 300, 400])
    assert result["count"] == 4
    assert result["mean_ms"] == 250
    assert result["p50_ms"] >= 200
    assert result["p95_ms"] >= 400
    assert result["percentiles_approximate"] is True


def test_empty_latency_summary_is_unavailable():
    assert summarize_latencies([])["mean_ms"] is None
