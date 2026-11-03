from __future__ import annotations

import pytest

from contract import ReadInput, SeedInput, UrlsInput
from plugin import canonical_states, log_info, read_log, scan_log
from plugin.log import build_log, canonical_state


def audit_by_tools(seed: int) -> dict:
    """What an agent submits after reading every page and canonicalizing every URL."""
    info = log_info(SeedInput(seed=seed), None)
    failed, counts = set(), {}
    for offset in range(0, info.events, info.page_size):
        events = read_log(ReadInput(seed=seed, offset=offset, limit=info.page_size), None).events
        states = canonical_states(UrlsInput(urls=[event.url for event in events]), None).states
        for event, found in zip(events, states, strict=True):
            key = (found.state, event.action)
            if key in failed:
                counts[key] = counts.get(key, 0) + 1
            if event.outcome.value == "fail":
                failed.add(key)
    return {"retries": [{"state": state, "action": action, "retry_count": count}
                        for (state, action), count in sorted(counts.items())]}


def test_a_seed_always_builds_the_same_log() -> None:
    assert build_log(42) == build_log(42)
    assert build_log(42) != build_log(43)


@pytest.mark.parametrize(
    ("url", "state"),
    [
        ("https://SHOP.example.com/cart/?sid=1a&ts=9", "shop.example.com/cart"),
        ("https://shop.example.com/search?sort=price&ad_id=4&q=laptop", "shop.example.com/search?q=laptop&sort=price"),
        ("https://shop.example.com/?utm_source=mail", "shop.example.com/"),
        ("https://shop.example.com/help?topic=returns#faq", "shop.example.com/help?topic=returns"),
    ],
)
def test_canonical_states_drop_only_the_noise(url: str, state: str) -> None:
    assert canonical_state(url) == state


@pytest.mark.parametrize("seed", range(200))
def test_the_tools_and_the_reference_agree(seed: int) -> None:
    reference = scan_log(SeedInput(seed=seed), None)
    found = audit_by_tools(seed)["retries"]
    assert found == [{"state": item.state, "action": item.action, "retry_count": item.retry_count}
                     for item in reference.retries]
    assert 90 <= len(reference.events) <= 140


def test_one_state_shows_up_under_many_raw_urls() -> None:
    events = build_log(7)
    by_state: dict[str, set[str]] = {}
    for event in events:
        by_state.setdefault(canonical_state(event.url), set()).add(event.url)
    assert all(len(urls) > 1 for urls in by_state.values())


def test_the_tools_refuse_reads_outside_the_log() -> None:
    total = log_info(SeedInput(seed=7), None).events
    with pytest.raises(ValueError, match="offset"):
        read_log(ReadInput(seed=7, offset=total, limit=5), None)
    with pytest.raises(ValueError, match="limit"):
        read_log(ReadInput(seed=7, offset=0, limit=251), None)
    with pytest.raises(ValueError, match="URLs"):
        canonical_states(UrlsInput(urls=["https://shop.example.com/cart"] * 251), None)
    with pytest.raises(ValueError, match="URL"):
        canonical_states(UrlsInput(urls=["shop.example.com/cart"]), None)
    with pytest.raises(ValueError, match="seed"):
        log_info(SeedInput(seed=-1), None)
