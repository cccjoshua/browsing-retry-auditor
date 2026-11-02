"""canonical_states: each URL's canonical state."""

from .checks import PAGE_SIZE, canonical_state, result


def verify_input(value):
    if not 1 <= len(value.urls) <= PAGE_SIZE:
        return result(False, f"give 1 to {PAGE_SIZE} URLs")
    if any("://" not in url for url in value.urls):
        return result(False, "every URL has a scheme, e.g. https://")
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    if [found.url for found in output_value.states] != input_value.urls:
        return result(False, "the states are not for the URLs given, in order")
    for found in output_value.states:
        if found.state != canonical_state(found.url):
            return result(False, f"{found.url} canonicalizes to {canonical_state(found.url)}, not {found.state}")
    return result(True, f"{len(output_value.states)} states")
