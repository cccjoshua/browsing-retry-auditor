"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    LOG_INFO = "log_info"
    READ_LOG = "read_log"
    CANONICAL_STATES = "canonical_states"
    SCAN_LOG = "scan_log"


class Task(Enum):
    AUDIT_RETRIES = "audit-retries"


class Outcome(Enum):
    OK = "ok"
    FAIL = "fail"


SEED = "The log's seed, 0 to 1000000: the same seed always builds the same log"
STATE = "A canonical page state: host and path in lower case, then the query parameters that matter, sorted"
ACTION = "The action taken, e.g. click:checkout"


@dataclass
class SeedInput(Output):
    seed: Annotated[int, SEED]


@dataclass
class LogInfoOutput(Output):
    seed: Annotated[int, SEED]
    events: Annotated[int, "How many events the log holds"]
    page_size: Annotated[int, "The most events one read_log call returns"]


@dataclass
class ReadInput(Output):
    seed: Annotated[int, SEED]
    offset: Annotated[int, "The index of the first event to read, from 0"]
    limit: Annotated[int, "How many events to read, 1 to 50"]


@dataclass
class LogEvent(Output):
    step: Annotated[int, "The event's step number, from 1"]
    url: Annotated[str, "The page's raw URL, with session, time and ad parameters"]
    action: Annotated[str, ACTION]
    outcome: Annotated[Outcome, "ok or fail"]


@dataclass
class LogPageOutput(Output):
    offset: Annotated[int, "The index of the first event returned"]
    events: Annotated[list[LogEvent], "The events, in log order; fewer than limit at the end of the log"]


@dataclass
class UrlsInput(Output):
    urls: Annotated[list[str], "Raw URLs from the log, 1 to 50"]


@dataclass
class CanonicalState(Output):
    url: Annotated[str, "The raw URL, as given"]
    state: Annotated[str, STATE]


@dataclass
class StatesOutput(Output):
    states: Annotated[list[CanonicalState], "Each URL's canonical state, in the order given"]


@dataclass
class Retry(Output):
    state: Annotated[str, STATE]
    action: Annotated[str, ACTION]
    retry_count: Annotated[int, "How many times the pair was attempted after an earlier attempt of it failed"]


@dataclass
class FullLogOutput(Output):
    events: Annotated[list[LogEvent], "Every event of the log, in order"]
    retries: Annotated[list[Retry], "Every retried pair, sorted by state then action"]


@dataclass
class RetriesOutput(Output):
    retries: Annotated[
        list[Retry],
        "Every (state, action) pair attempted again after an earlier attempt of the same pair failed, with its count",
    ]


TOOLS = {
    Tool.LOG_INFO: (SeedInput, LogInfoOutput),
    Tool.READ_LOG: (ReadInput, LogPageOutput),
    Tool.CANONICAL_STATES: (UrlsInput, StatesOutput),
    Tool.SCAN_LOG: (SeedInput, FullLogOutput),
}
TASKS = {
    Task.AUDIT_RETRIES: (SeedInput, RetriesOutput),
}
