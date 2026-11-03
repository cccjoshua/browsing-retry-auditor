from __future__ import annotations

import copy
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output
from test_log import audit_by_tools

import verifier
from contract import TASKS, TOOLS, FullLogOutput, ReadInput, SeedInput, Task, Tool, UrlsInput
from plugin import canonical_states, log_info, read_log, scan_log

TASK = "audit-retries"
SEEDS = range(60)


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def verify_task(seed: int, output: dict, reference: FullLogOutput | None, workspace: Path) -> dict:
    given, made = TASKS[Task(TASK)]
    pinned = None if reference is None else build_output(plain_output(reference), FullLogOutput)
    return verifier.verify_task(TASK, build_output({"seed": seed}, given), build_output(output, made), pinned,
                                str(workspace))


def verify_input(tool: str, value: dict) -> dict:
    return verifier.verify_input(tool, build_output(value, TOOLS[Tool(tool)][0]))


def verify_output(tool: str, given: dict, made: dict) -> dict:
    given_class, made_class = TOOLS[Tool(tool)]
    return verifier.verify_output(tool, build_output(given, given_class), build_output(made, made_class), "")


def reference(seed: int) -> FullLogOutput:
    return scan_log(SeedInput(seed=seed), None)


# Correct


@pytest.mark.parametrize("seed", SEEDS)
def test_approves_the_true_retries_in_any_order(seed: int, tmp_path: Path) -> None:
    found = audit_by_tools(seed)
    verdict = verify_task(seed, found, reference(seed), tmp_path)
    assert verdict["valid"] is True and verdict["score"] == 1.0
    flipped = {"retries": found["retries"][::-1]}
    assert verify_task(seed, flipped, reference(seed), tmp_path)["valid"] is True


# Incorrect


@pytest.mark.parametrize("seed", SEEDS)
def test_refuses_a_missed_pair_or_a_wrong_count(seed: int, tmp_path: Path) -> None:
    found = audit_by_tools(seed)
    pairs = len(found["retries"])
    missed = {"retries": found["retries"][1:]}
    verdict = verify_task(seed, missed, reference(seed), tmp_path)
    assert verdict["valid"] is False and "1 missing" in verdict["message"]
    assert verdict["score"] == pytest.approx((pairs - 1) / pairs)
    miscounted = copy.deepcopy(found)
    miscounted["retries"][0]["retry_count"] += 1
    verdict = verify_task(seed, miscounted, reference(seed), tmp_path)
    assert verdict["valid"] is False and "1 miscounted" in verdict["message"]


def test_refuses_a_pair_that_was_never_retried(tmp_path: Path) -> None:
    found = audit_by_tools(7)
    retried = {(item["state"], item["action"]) for item in found["retries"]}
    event = next(event for event in reference(7).events
                 if (canonical_states(UrlsInput(urls=[event.url]), None).states[0].state, event.action) not in retried)
    state = canonical_states(UrlsInput(urls=[event.url]), None).states[0].state
    extra = {"retries": found["retries"] + [{"state": state, "action": event.action, "retry_count": 1}]}
    verdict = verify_task(7, extra, reference(7), tmp_path)
    assert verdict["valid"] is False and "1 not retried" in verdict["message"]


def test_refuses_raw_urls_in_place_of_canonical_states(tmp_path: Path) -> None:
    found = copy.deepcopy(audit_by_tools(7))
    raw = next(event.url for event in reference(7).events
               if canonical_states(UrlsInput(urls=[event.url]), None).states[0].state == found["retries"][0]["state"])
    found["retries"][0]["state"] = raw
    verdict = verify_task(7, found, reference(7), tmp_path)
    assert verdict["valid"] is False and "missing" in verdict["details"] and "extra" in verdict["details"]


def test_refuses_counting_every_attempt_instead_of_retries(tmp_path: Path) -> None:
    found = copy.deepcopy(audit_by_tools(7))
    for item in found["retries"]:
        item["retry_count"] += 1  # the first failed attempt counted too
    verdict = verify_task(7, found, reference(7), tmp_path)
    assert verdict["valid"] is False and verdict["score"] == 0.0


def test_refuses_another_seeds_retries(tmp_path: Path) -> None:
    assert verify_task(0, audit_by_tools(1), reference(0), tmp_path)["valid"] is False


# Missing


def test_refuses_an_empty_report_or_a_missing_reference(tmp_path: Path) -> None:
    verdict = verify_task(7, {"retries": []}, reference(7), tmp_path)
    assert verdict["valid"] is False and verdict["score"] == 0.0
    verdict = verify_task(7, audit_by_tools(7), None, tmp_path)
    assert verdict["valid"] is False and "no reference" in verdict["message"]


# Malformed


def test_refuses_a_pair_twice_or_a_zero_count(tmp_path: Path) -> None:
    found = audit_by_tools(7)
    twice = {"retries": found["retries"] + found["retries"][:1]}
    assert "twice" in verify_task(7, twice, reference(7), tmp_path)["message"]
    zero = copy.deepcopy(found)
    zero["retries"][0]["retry_count"] = 0
    assert "at least once" in verify_task(7, zero, reference(7), tmp_path)["message"]


@pytest.mark.parametrize(
    "output",
    [
        {},
        {"retries": [{"state": "shop.example.com/cart", "action": "click:checkout"}]},
        {"retries": [{"state": "shop.example.com/cart", "action": "click:checkout", "retry_count": "two"}]},
        {"retries": "shop.example.com/cart click:checkout 2"},
    ],
)
def test_the_contract_refuses_a_malformed_report(output: dict) -> None:
    with pytest.raises(Exception):  # noqa: B017 - slimconfig's error type is its own
        build_output(output, TASKS[Task(TASK)][1])


def test_refuses_malformed_tool_input() -> None:
    assert verify_input("read_log", {"seed": 7, "offset": 0, "limit": 250})["valid"] is True
    assert verify_input("read_log", {"seed": 7, "offset": 0, "limit": 251})["valid"] is False
    assert verify_input("read_log", {"seed": 7, "offset": -1, "limit": 20})["valid"] is False
    assert verify_input("read_log", {"seed": 7, "offset": 0, "limit": 0})["valid"] is False
    assert verify_input("canonical_states", {"urls": []})["valid"] is False
    assert verify_input("canonical_states", {"urls": ["shop.example.com/cart"]})["valid"] is False
    assert verify_input("log_info", {"seed": 1_000_001})["valid"] is False


# Boundary


def test_a_log_with_no_retries_takes_an_empty_report(tmp_path: Path) -> None:
    seed = next(seed for seed in range(2000) if not reference(seed).retries)
    assert verify_task(seed, {"retries": []}, reference(seed), tmp_path)["valid"] is True


def test_the_whole_log_reads_in_one_call_and_its_urls_canonicalize_in_one_call(tmp_path: Path) -> None:
    for seed in (0, 3, 7, 1_000_000, *range(200)):
        total = log_info(SeedInput(seed=seed), None).events
        assert total < 250
        whole = read_log(ReadInput(seed=seed, offset=0, limit=250), None)
        assert len(whole.events) == total and whole.events[-1].step == total
        states = canonical_states(UrlsInput(urls=[event.url for event in whole.events]), None)
        assert len(states.states) == total


def test_the_last_partial_page_counts(tmp_path: Path) -> None:
    seed = next(seed for seed in range(100) if log_info(SeedInput(seed=seed), None).events % 50)
    total = log_info(SeedInput(seed=seed), None).events
    last = read_log(ReadInput(seed=seed, offset=total - total % 50, limit=50), None)
    assert len(last.events) == total % 50 and last.events[-1].step == total


def test_a_success_between_failures_keeps_the_later_attempts_retries(tmp_path: Path) -> None:
    found = plain_output(reference(7))
    url = "https://shop.example.com/cart?sid=1"
    found["events"] = [
        {"step": 1, "url": url, "action": "click:checkout", "outcome": "fail"},
        {"step": 2, "url": url.replace("sid=1", "sid=2"), "action": "click:checkout", "outcome": "ok"},
        {"step": 3, "url": url.upper().replace("HTTPS", "https"), "action": "click:checkout", "outcome": "ok"},
        {"step": 4, "url": url, "action": "click:remove-item", "outcome": "ok"},
        {"step": 5, "url": url, "action": "click:remove-item", "outcome": "ok"},
    ]
    found["retries"] = [{"state": "shop.example.com/cart", "action": "click:checkout", "retry_count": 2}]
    pinned = build_output(found, FullLogOutput)
    assert verify_output("scan_log", {"seed": 7}, found)["valid"] is True
    assert verify_task(7, {"retries": found["retries"]}, pinned, tmp_path)["valid"] is True


# Each tool's own checks


def test_tool_outputs_pass_their_checks_and_tampered_ones_do_not() -> None:
    info = plain_output(log_info(SeedInput(seed=7), None))
    assert verify_output("log_info", {"seed": 7}, info)["valid"] is True
    assert verify_output("log_info", {"seed": 8}, info)["valid"] is False

    given = {"seed": 7, "offset": 20, "limit": 20}
    page = plain_output(read_log(ReadInput(**given), None))
    assert verify_output("read_log", given, page)["valid"] is True
    assert verify_output("read_log", given, page | {"events": page["events"][::-1]})["valid"] is False

    urls = [event["url"] for event in page["events"]]
    states = plain_output(canonical_states(UrlsInput(urls=urls), None))
    assert verify_output("canonical_states", {"urls": urls}, states)["valid"] is True
    states["states"][0]["state"] = urls[0]
    assert verify_output("canonical_states", {"urls": urls}, states)["valid"] is False

    found = plain_output(reference(7))
    assert verify_output("scan_log", {"seed": 7}, found)["valid"] is True
    assert verify_output("scan_log", {"seed": 7}, found | {"retries": found["retries"][1:]})["valid"] is False


def test_the_verdict_is_the_same_every_time(tmp_path: Path) -> None:
    found = {"retries": audit_by_tools(11)["retries"][1:]}
    verdicts = [verify_task(11, found, reference(11), tmp_path) for _ in range(3)]
    assert verdicts[0] == verdicts[1] == verdicts[2]
