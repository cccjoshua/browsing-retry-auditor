"""The plugin's tools: each takes its contract input and the workspace."""

from __future__ import annotations

from pathlib import Path

from contract import (
    CanonicalState,
    FullLogOutput,
    LogEvent,
    LogInfoOutput,
    LogPageOutput,
    ReadInput,
    Retry,
    SeedInput,
    StatesOutput,
    UrlsInput,
)
from plugin.log import PAGE_SIZE, build_log, canonical_state, retries


def _event(event) -> LogEvent:
    return LogEvent(step=event.step, url=event.url, action=event.action, outcome=event.outcome)


def log_info(given: SeedInput, workspace: Path) -> LogInfoOutput:
    return LogInfoOutput(seed=given.seed, events=len(build_log(given.seed)), page_size=PAGE_SIZE)


def read_log(given: ReadInput, workspace: Path) -> LogPageOutput:
    events = build_log(given.seed)
    if not 1 <= given.limit <= PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {PAGE_SIZE}")
    if not 0 <= given.offset < len(events):
        raise ValueError(f"offset must be between 0 and {len(events) - 1}")
    return LogPageOutput(
        offset=given.offset, events=[_event(event) for event in events[given.offset : given.offset + given.limit]]
    )


def canonical_states(given: UrlsInput, workspace: Path) -> StatesOutput:
    if not 1 <= len(given.urls) <= PAGE_SIZE:
        raise ValueError(f"give 1 to {PAGE_SIZE} URLs")
    return StatesOutput(states=[CanonicalState(url=url, state=canonical_state(url)) for url in given.urls])


def scan_log(given: SeedInput, workspace: Path) -> FullLogOutput:
    """The reference: the whole log and its retries, run out of the agent's sight."""
    events = build_log(given.seed)
    return FullLogOutput(
        events=[_event(event) for event in events],
        retries=[Retry(state=state, action=action, retry_count=count) for state, action, count in retries(events)],
    )
