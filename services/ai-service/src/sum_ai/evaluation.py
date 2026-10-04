"""Ranking quality requires explicit, current relevant-chunk labels."""

from sum_contracts.ai import EvaluationScores


def evaluate(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> EvaluationScores | None:
    if not 1 <= k <= 10:
        raise ValueError("k must be between 1 and 10")
    if not relevant_ids:
        return None
    ranking = list(dict.fromkeys(retrieved_ids))[:k]
    hits = len(set(ranking) & relevant_ids)
    first = next((rank for rank, chunk in enumerate(ranking, 1) if chunk in relevant_ids), None)
    return EvaluationScores(recall_at_k=hits / len(relevant_ids), precision_at_k=hits / k,
                            mrr=1 / first if first else 0, k=k)
