"""scan_log, the reference: the whole log and its retries."""

from .checks import result, retry_counts, seed_problem


def verify_input(value):
    problem = seed_problem(value.seed)
    return result(problem is None, problem or "input is valid")


def verify_output(input_value, output_value, workspace):
    steps = [event.step for event in output_value.events]
    if not steps or steps != list(range(1, len(steps) + 1)):
        return result(False, "the log's steps run 1, 2, 3, ...")
    if any("://" not in event.url for event in output_value.events):
        return result(False, "every event has a URL with a scheme")
    expected = sorted(retry_counts(output_value.events).items())
    given = [((found.state, found.action), found.retry_count) for found in output_value.retries]
    if given != expected:
        return result(False, "the retries are not the ones the log gives")
    return result(True, "reference is consistent", events=len(steps), retried_pairs=len(expected))
