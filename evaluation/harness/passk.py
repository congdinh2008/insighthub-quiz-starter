"""pass^k and pass@k over repeated runs of the same case."""
from collections import defaultdict


def aggregate(runs):
    """runs: iterable of {"case_id", "passed"} -> per-case pass^k (all runs pass) and pass@k (any run passes)."""
    by_case = defaultdict(list)
    for run in runs:
        by_case[run["case_id"]].append(bool(run["passed"]))
    return {
        case: {"k": len(results), "pass_hat_k": all(results), "pass_at_k": any(results), "passes": sum(results)}
        for case, results in by_case.items()
    }


def suite_rate(per_case, metric="pass_hat_k"):
    if not per_case:
        return 0.0
    return sum(v[metric] for v in per_case.values()) / len(per_case)
