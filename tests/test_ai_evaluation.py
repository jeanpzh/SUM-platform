import pytest
from sum_ai.evaluation import evaluate


def test_labeled_ranking_scores():
    result = evaluate(["irrelevant", "relevant"], {"relevant", "missing"}, 4)
    assert result.recall_at_k == 0.5
    assert result.precision_at_k == 0.25
    assert result.mrr == 0.5


def test_no_labels_are_unavailable_and_duplicates_do_not_inflate_scores():
    assert evaluate(["one"], set(), 4) is None
    result = evaluate(["one", "one", "two"], {"one", "two"}, 4)
    assert result.recall_at_k == 1
    assert result.precision_at_k == 0.5
    with pytest.raises(ValueError):
        evaluate(["one"], {"one"}, 0)
