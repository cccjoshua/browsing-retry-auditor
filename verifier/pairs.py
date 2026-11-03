"""pair_attempts: the log grouped by (state, action), each pair's outcomes in step order."""

from .checks import canonical_state, result, seed_problem


def verify_input(value):
    problem = seed_problem(value.seed)
    return result(problem is None, problem or "input is valid")


def verify_output(input_value, output_value, workspace):
    pairs = output_value.pairs
    if not pairs:
        return result(False, "a log has at least one pair")
    keys = [(pair.state, pair.action) for pair in pairs]
    if len(set(keys)) != len(keys):
        return result(False, "a pair is listed twice")
    for pair in pairs:
        if not pair.outcomes:
            return result(False, f"{pair.state} {pair.action} has no attempts")
        if not pair.action.strip() or canonical_state("https://" + pair.state) != pair.state:
            return result(False, f"{pair.state!r} is not a canonical state with an action")
    return result(True, "pairs are well formed", pairs=len(pairs), attempts=sum(len(p.outcomes) for p in pairs))
