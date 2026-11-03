# Browsing Log Retry Auditor

A `nanoagent.plugin/v0001` plugin. An agent audits a web agent's browsing log: `pair_attempts` canonicalizes
its URLs into page states and lists each (state, action) pair with its outcomes in step order, and the agent
reports every pair that was attempted again after an earlier attempt of it failed, with the number of such
retries. A deterministic verifier canonicalizes the raw log itself, counts the retries and checks the report.

Each log is built from an integer seed alone (SHA-256 of the seed and a counter): 90 to 140 events over
8 to 11 page states. URLs of one state differ in host case, a trailing slash, parameter order and
noise parameters (`sid`, `ts`, `ad_id`, `utm_source`). Some actions always fail, some fail now and
then, and after a failure the agent often tries again. No network is used.

## Tools

| Tool | Does | Code |
|---|---|---|
| `log_info` | Says how many events the log holds and the page size | `src/plugin/tools.py` |
| `read_log` | Reads up to 250 events from an offset, each with its canonical state | `src/plugin/tools.py` |
| `canonical_states` | Canonicalizes up to 250 raw URLs | `src/plugin/tools.py` |
| `pair_attempts` | Groups the whole log by (canonical state, action), each pair's outcomes in step order | `src/plugin/tools.py` |
| `scan_log` | The whole log and its retries: the task's reference, never shown to the agent | `src/plugin/tools.py` |

The log itself is built in `src/plugin/log.py`.

### Tasks

| Task | Does | Runner |
|---|---|---|
| `audit-retries` | Report every (state, action) retried after a failure, with its count | `agent`, with `pair_attempts`; reference `scan_log` |

A state is the host and path in lower case without a trailing slash, then the query parameters that
are not noise, sorted. An attempt is a retry when an earlier attempt of the same pair failed. The
verifier (`verifier/audit.py`) canonicalizes and counts the reference log itself, and the report is
valid only when every pair and count matches. Its score is the share of pairs it gets exactly right.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs (none)
├── src/plugin/      # the MCP server, the log generator and the tools
├── tests/           # tests of the log, the tools and the verifier
├── ui/              # outputs are drawn from their JSON Schema
├── product/         # the product page: product.yaml and icon.svg
└── verifier/        # deterministic verifier package
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

Publishing checks every plugin rule: push the plugin to a public GitHub repository and submit its
URL on RUSH Lab.
