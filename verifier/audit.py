"""audit-retries: the agent's retries, compared with the retries counted on the reference log.

Valid only when the reported pairs and counts match exactly, with no pair twice. The score is the
share of pairs (reported or true) the report gets exactly right.
"""

from .checks import result, retry_counts


def verify_task(arguments, output, reference, workspace):
    """``output``: a contract RetriesOutput; ``reference``: the scan_log FullLogOutput of the same seed."""
    if reference is None:
        return result(False, "no reference log: the retries cannot be checked")
    keys = [(found.state, found.action) for found in output.retries]
    if len(set(keys)) != len(keys):
        return result(False, "a (state, action) pair is reported twice")
    if any(found.retry_count < 1 for found in output.retries):
        return result(False, "every reported pair was retried at least once")
    given = {(found.state, found.action): found.retry_count for found in output.retries}
    expected = retry_counts(reference.events)
    missing = sorted(f"{state} {action}" for state, action in set(expected) - set(given))
    extra = sorted(f"{state} {action}" for state, action in set(given) - set(expected))
    miscounted = sorted(
        f"{state} {action}: {given[(state, action)]} given, {count} counted"
        for (state, action), count in expected.items()
        if (state, action) in given and given[(state, action)] != count
    )
    pairs = set(given) | set(expected)
    right = sum(1 for key in pairs if given.get(key) == expected.get(key))
    score = right / len(pairs) if pairs else 1.0
    if missing or extra or miscounted:
        parts = [f"{len(found)} {name}" for name, found in
                 (("missing", missing), ("not retried", extra), ("miscounted", miscounted)) if found]
        details = {name: found for name, found in
                   (("missing", missing), ("extra", extra), ("miscounted", miscounted)) if found}
        return result(False, "; ".join(parts), score=score, **details)
    return result(True, f"all {len(expected)} retried pairs, {sum(expected.values())} retries", pairs=len(expected))
