"""Checks shared by the tool verifiers. Pure functions of their arguments.

The verifier canonicalizes URLs and counts retries itself, with the rules the task states.
"""

from contract import Outcome

MAX_SEED = 1_000_000
PAGE_SIZE = 50
NOISE = frozenset({"sid", "session", "ts", "t", "ad", "ad_id", "utm_source", "utm_campaign", "ref"})


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def seed_problem(seed):
    if not 0 <= seed <= MAX_SEED:
        return f"seed must be between 0 and {MAX_SEED}"
    return None


def canonical_state(url):
    """Host and path in lower case without a trailing slash, then the parameters that matter, sorted."""
    rest = url.split("://", 1)[1].split("#", 1)[0]
    location, _, query = rest.partition("?")
    host, _, path = location.partition("/")
    path = "/" + path.lower().rstrip("/") if path.strip("/") else "/"
    kept = sorted(part for part in query.split("&") if part and part.split("=", 1)[0].lower() not in NOISE)
    return host.lower() + path + ("?" + "&".join(kept) if kept else "")


def retry_counts(events):
    """{(state, action): count} for every pair attempted after an earlier attempt of it failed."""
    failed, counts = set(), {}
    for event in events:
        key = (canonical_state(event.url), event.action)
        if key in failed:
            counts[key] = counts.get(key, 0) + 1
        if event.outcome is Outcome.FAIL:
            failed.add(key)
    return counts
