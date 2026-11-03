"""read_log: one page of events."""

from .checks import PAGE_SIZE, canonical_state, result, seed_problem


def verify_input(value):
    problem = seed_problem(value.seed)
    if problem is None and value.offset < 0:
        problem = "offset must not be negative"
    if problem is None and not 1 <= value.limit <= PAGE_SIZE:
        problem = f"limit must be between 1 and {PAGE_SIZE}"
    return result(problem is None, problem or "input is valid")


def verify_output(input_value, output_value, workspace):
    if output_value.offset != input_value.offset:
        return result(False, "the page starts at another offset")
    events = output_value.events
    if not 1 <= len(events) <= input_value.limit:
        return result(False, "a page holds 1 to limit events")
    steps = [event.step for event in events]
    if steps != list(range(input_value.offset + 1, input_value.offset + 1 + len(events))):
        return result(False, "the events are not the steps from offset + 1, in order")
    if any("://" not in event.url or not event.action.strip() for event in events):
        return result(False, "every event has a URL and an action")
    if any(event.state != canonical_state(event.url) for event in events):
        return result(False, "every event's state is its URL's canonical state")
    return result(True, f"steps {steps[0]} to {steps[-1]}")
