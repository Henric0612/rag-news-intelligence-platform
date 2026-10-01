"""Pure retrieval metric mathematics for D2; no model or database imports."""

import math


def _inputs(retrieved_ids, relevance, k):
    if type(k) is not int or k < 1:
        raise ValueError("k must be a positive integer")
    if len(retrieved_ids) != len(set(retrieved_ids)):
        raise ValueError("retrieved IDs must be unique")
    if any(type(grade) is not int or grade not in (0, 1, 2)
           for grade in relevance.values()):
        raise ValueError("relevance grades must be 0, 1, or 2")


def recall_at_k(retrieved_ids, relevance, k, *, answerable):
    """Fraction of grade >=1 items retrieved; None excludes zero-relevant queries.

    No-answer questions return None even when they have grade-1 candidates.
    """
    _inputs(retrieved_ids, relevance, k)
    if type(answerable) is not bool:
        raise ValueError("answerable must be boolean")
    if not answerable:
        return None
    relevant = {item_id for item_id, grade in relevance.items() if grade > 0}
    if not relevant:
        return None
    return len(relevant.intersection(retrieved_ids[:k])) / len(relevant)


def ndcg_at_k(retrieved_ids, relevance, k):
    """nDCG with exponential gain (2**grade - 1) and log2(rank + 1)."""
    _inputs(retrieved_ids, relevance, k)
    def dcg(grades):
        return sum((2 ** grade - 1) / math.log2(rank + 1)
                   for rank, grade in enumerate(grades, start=1))
    ideal = dcg(sorted(relevance.values(), reverse=True)[:k])
    if ideal == 0:
        return 0.0
    actual = dcg([relevance.get(item_id, 0) for item_id in retrieved_ids[:k]])
    return actual / ideal


def mrr_at_k(retrieved_ids, relevance, k):
    """Reciprocal rank of the first grade >=1 item, or zero if absent."""
    _inputs(retrieved_ids, relevance, k)
    for rank, item_id in enumerate(retrieved_ids[:k], start=1):
        if relevance.get(item_id, 0) > 0:
            return 1 / rank
    return 0.0
