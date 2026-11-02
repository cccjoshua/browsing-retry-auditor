"""The browsing log: what a web agent did, built from a seed alone.

Each event is a raw URL, an action and its outcome. URLs of one page state differ in host case, a
trailing slash, parameter order and noise parameters (session, time, ads, tracking), so the log must
be canonicalized before attempts can be compared. Some actions always fail, some fail now and then,
and after a failure the agent often tries the same action again: those repeats are the retries.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from contract import Outcome

MAX_SEED = 1_000_000
PAGE_SIZE = 50
HOST = "shop.example.com"
NOISE = frozenset({"sid", "session", "ts", "t", "ad", "ad_id", "utm_source", "utm_campaign", "ref"})
STATES = (
    ("/cart", (), ("click:checkout", "click:remove-item", "click:apply-coupon")),
    ("/search", ("q=headphones",), ("click:first-result", "click:next-page", "click:filter-brand")),
    ("/search", ("q=laptop", "sort=price"), ("click:first-result", "click:compare", "click:next-page")),
    ("/product/4471", ("tab=reviews",), ("click:add-to-cart", "click:helpful", "click:write-review")),
    ("/product/4471", (), ("click:add-to-cart", "click:size-guide", "click:wishlist")),
    ("/product/9020", (), ("click:add-to-cart", "click:wishlist", "click:share")),
    ("/checkout/shipping", (), ("submit:address", "click:back-to-cart", "click:express")),
    ("/checkout/payment", (), ("submit:card", "click:apply-gift-card", "click:back")),
    ("/account/orders", ("page=2",), ("click:track", "click:return", "click:invoice")),
    ("/account/settings", (), ("submit:profile", "click:change-password", "click:delete-account")),
    ("/help", ("topic=returns",), ("click:contact", "submit:chat", "click:faq")),
    ("/deals", (), ("click:claim", "click:next-deal", "click:subscribe")),
)


@dataclass(frozen=True)
class Event:
    step: int
    url: str
    action: str
    outcome: Outcome


def canonical_state(url: str) -> str:
    """Host and path in lower case without a trailing slash, then the parameters that matter, sorted."""
    if "://" not in url:
        raise ValueError(f"{url!r} is not a URL with a scheme")
    rest = url.split("://", 1)[1].split("#", 1)[0]
    location, _, query = rest.partition("?")
    host, _, path = location.partition("/")
    path = "/" + path.lower().rstrip("/") if path.strip("/") else "/"
    kept = sorted(part for part in query.split("&") if part and part.split("=", 1)[0].lower() not in NOISE)
    return host.lower() + path + ("?" + "&".join(kept) if kept else "")


class Draws:
    """A deterministic stream of choices from the seed: SHA-256 of the seed and a counter."""

    def __init__(self, seed: int) -> None:
        self.seed, self.count = seed, 0

    def below(self, bound: int) -> int:
        digest = hashlib.sha256(f"retry-auditor:{self.seed}:{self.count}".encode()).digest()
        self.count += 1
        return int.from_bytes(digest[:8], "big") % bound

    def pick(self, items):
        return items[self.below(len(items))]

    def shuffled(self, items):
        items = list(items)
        for index in range(len(items) - 1, 0, -1):
            other = self.below(index + 1)
            items[index], items[other] = items[other], items[index]
        return items


def _raw_url(draws: Draws, path: str, params: tuple[str, ...]) -> str:
    host = draws.pick((HOST, HOST, "Shop.Example.com", "SHOP.example.com"))
    shown = path + ("/" if draws.below(3) == 0 else "")
    noise = [
        f"sid={draws.below(16 ** 8):08x}",
        f"ts={1_760_000_000 + draws.below(1_000_000)}",
        *(f"ad_id={draws.below(10_000)}" for _ in range(draws.below(2))),
        *(f"utm_source={draws.pick(('mail', 'feed', 'banner'))}" for _ in range(draws.below(2))),
    ]
    query = "&".join(draws.shuffled(list(params) + noise))
    return f"https://{host}{shown}?{query}"


def build_log(seed: int) -> tuple[Event, ...]:
    if not 0 <= seed <= MAX_SEED:
        raise ValueError(f"seed must be between 0 and {MAX_SEED}")
    draws = Draws(seed)
    states = draws.shuffled(STATES)[: 8 + draws.below(4)]
    modes = {}
    for path, params, actions in states:
        for action in actions:
            roll = draws.below(20)
            modes[(path, params, action)] = "broken" if roll == 0 else "flaky" if roll < 5 else "fine"
    pairs = list(modes)
    total = 90 + draws.below(51)  # 90 to 140 events
    events: list[Event] = []
    while len(events) < total:
        path, params, action = pair = draws.pick(pairs)
        repeats = 1
        while repeats and len(events) < total:
            repeats -= 1
            mode = modes[pair]
            failed = mode == "broken" or (mode == "flaky" and draws.below(5) < 2)
            outcome = Outcome.FAIL if failed else Outcome.OK
            events.append(Event(len(events) + 1, _raw_url(draws, path, params), action, outcome))
            if failed and draws.below(2) == 0:
                repeats = 1 + draws.below(2)  # the agent tries the same action again, once or twice
    return tuple(events)


def retries(events) -> list[tuple[str, str, int]]:
    """(state, action, count) for every pair attempted after an earlier attempt of it failed, sorted."""
    failed: set[tuple[str, str]] = set()
    counts: dict[tuple[str, str], int] = {}
    for event in events:
        key = (canonical_state(event.url), event.action)
        if key in failed:
            counts[key] = counts.get(key, 0) + 1
        if event.outcome is Outcome.FAIL:
            failed.add(key)
    return [(state, action, count) for (state, action), count in sorted(counts.items())]
