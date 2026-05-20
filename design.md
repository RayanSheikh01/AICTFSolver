# AI-Assisted CTF Solver Agent — Design

**Date:** 2026-05-20
**Status:** Draft, approved for planning

## 1. Overview

An autonomous agent that takes a CTF challenge description, runs reconnaissance and exploitation tools (nmap, sqlmap, gobuster, hydra, etc.) inside a sandboxed Docker container, iterates toward a flag, and emits a publishable markdown write-up of its reasoning chain.

**v1 scope:** Web exploitation and Network/recon categories. Other categories (crypto, forensics, RE, pwn) are out of scope for v1 but the tool registry is designed so they can be added without graph changes.

**Primary purpose:** Fully autonomous solver — the agent drives the loop; the human only confirms candidate flags.

## 2. Architecture

LangGraph state machine with explicit phase nodes and a re-plan loop:

```
Triage → Recon → Hypothesize → Exploit → Verify → {Hypothesize | Recon | HumanConfirm} → Writeup
```

| Node | Role |
|------|------|
| **Triage** | Parses challenge description + target. Classifies category (web vs network), extracts target surface, sets initial goals. Runs once. |
| **Recon** | Runs information-gathering tools (nmap, whatweb, curl/headers, gobuster, nikto). Appends structured findings. Re-entered if Verify decides data is thin. |
| **Hypothesize** | LLM reasoning step. Produces 1–3 ranked attack hypotheses from current findings. No tool calls — pure reasoning, logged verbatim for the write-up. |
| **Exploit** | Executes the top hypothesis via the appropriate registered tool (sqlmap, curl_exploit, hydra, …). Captures full output. |
| **Verify** | Checks for candidate flags via regex; evaluates exploit signal; routes:<br>• candidate flag → HumanConfirm<br>• new data, no flag → Hypothesize<br>• failure + thin findings → Recon<br>• budget exceeded → HumanConfirm("need-help") |
| **HumanConfirm** | Surfaces candidate flag(s) to the user. Confirm → Writeup. Reject → Hypothesize (with rejection noted). |
| **Writeup** | Terminal node. Consumes structured trace; emits polished markdown. |

Every node appends to a single append-only `reasoning_log` in state, tagged by node. The log is what the Writeup node consumes.

## 3. State & Tool Registry

### 3.1 Shared state

```python
class AgentState(TypedDict):
    # Inputs
    challenge: ChallengeSpec          # description, target, category hint, flag_format,
                                      # allowed_targets, dangerous_tools_allowed, budget

    # Knowledge (append-only)
    findings: list[Finding]           # {source_tool, kind, value, confidence}
    hypotheses: list[Hypothesis]      # {id, text, rank, status: open|tried|disproved}
    attempts: list[Attempt]           # {hypothesis_id, tool, args, exit_code, summary}
    candidate_flags: list[str]

    # Control
    phase: Literal["triage","recon","hypothesize","exploit","verify",
                   "human_confirm","writeup"]
    loop_budget: BudgetCounters       # iterations, wall_clock_s, tool_calls (used/max)

    # Output
    reasoning_log: list[LogEntry]     # {node, ts, kind: thought|command|output|decision,
                                      #  content}
    human_messages: list[HumanTurn]   # confirm/reject events with rationale
```

### 3.2 Tool registry

Each tool is a typed wrapper, not a free shell. Schema:

```python
class ToolSpec:
    name: str
    category: Literal["recon", "exploit", "utility"]
    args_schema: type[BaseModel]
    docker_image: str                 # usually "ctf-agent-runner"
    command_template: list[str]
    parser: Callable[[ToolOutput], list[Finding]]
    dangerous: bool = False           # requires explicit ChallengeSpec opt-in
    default_timeout_s: int
```

**v1 tools:**
- **Recon:** `nmap`, `whatweb`, `curl_headers`, `gobuster`, `nikto`
- **Exploit (web):** `sqlmap`, `curl_exploit` (templated request with payload), `hydra` (dangerous, rate-limited)
- **Utility:** `regex_extract`, `decode` (base64/url/hex), `flag_scan` (runs flag-format regex over any blob)

The Hypothesize and Exploit nodes see only the tool registry's names + arg schemas — never raw shell. Adding a tool = registering a new `ToolSpec`; the graph is unchanged.

## 4. Docker Execution & Safety

**One container per run** (not per tool call) — preserves wordlists, downloaded artifacts, and intermediate files across steps via a shared `/work` volume.

- **Image:** `ctf-agent-runner`, built on `kalilinux/kali-rolling` with pinned versions of all v1 tools + `python3`, `requests`, `pwntools`. Built once, cached.
- **Lifecycle:** Agent process (LangGraph + LLM calls) runs on host. Per-run container started with `--rm`, mounts `/work` to host run-dir, `/tmp` as tmpfs.
- **Invocation:** Executor calls `docker exec <container> <tool> <args>` via a thin wrapper. Stdout/stderr/exit captured; raw logs to `/work/raw/<step>.log`; parsed findings to state.

### 4.1 Safety guardrails (defense in depth)

1. **Target allowlist** — `ChallengeSpec.allowed_targets` (hosts/CIDRs). Every tool wrapper validates target args against the list *before* exec. Rejection is logged as a `decision` entry. No allowlist → agent refuses to run.
2. **Network egress filter** — container runs on a custom Docker network with iptables permitting only allowed targets + DNS.
3. **Resource caps** — `--cpus`, `--memory`, per-tool wall-clock timeout enforced by the wrapper.
4. **Budget enforcement** — `loop_budget` (max iterations, max tool calls, max wall time) checked at every Verify; exceeding routes to HumanConfirm with `"budget-exceeded"`.
5. **Dangerous-tool gate** — tools flagged `dangerous: true` (e.g., `hydra`) require explicit opt-in in `ChallengeSpec`; usage emits a prominent log entry.

**Artifact retention:** on run end, `/work/` is copied to `runs/<run-id>/` on host — raw outputs, structured trace, reasoning log, and write-up.

## 5. Write-up Generator

A first-class output, not a summarizer. Because every node appends typed entries to `reasoning_log`, generation is mostly a structured-to-prose transform with an LLM polish pass.

**Inputs:** the full `AgentState` at terminal success.

**Pipeline (single Writeup node, three sub-steps):**

1. **Section assembly (deterministic).** Group `reasoning_log` entries by phase node into a fixed skeleton:
   - *Triage* → "Challenge Overview"
   - *Recon* → "Reconnaissance" (per-tool: command, key findings, trimmed output snippet)
   - *Hypothesize* → "Analysis" (ranked hypotheses, basis, which were tried)
   - *Exploit* → "Exploitation" (winning attempt: command, payload, output excerpt)
   - *Verify* → "Flag Recovery"
   - Plus a **"Dead Ends"** section auto-built from disproved hypotheses + failed attempts.
2. **LLM polish pass.** One call per section: takes structured draft + raw log slice, rewrites to clean prose, keeps commands/outputs verbatim in fenced code blocks. Prompt explicitly forbids inventing steps.
3. **Assembly + frontmatter.** Concatenate sections; prepend YAML frontmatter (`title`, `category`, `tools_used`, `duration`, `difficulty_self_rating`); append "Tools & Commands Reference" auto-extracted from `attempts`. Output: `runs/<run-id>/writeup.md`.

**Faithfulness guard:** a deterministic post-check parses the polished markdown, extracts every fenced command/output, and verifies each appears in the raw trace. Mismatches abort with a diff. Prevents fabrication.

Markdown-only output in v1 — structured for direct paste into Hugo/Jekyll/Notion.

## 6. Testing Strategy

The agent is non-deterministic; tests target the deterministic seams.

| Layer | What's tested | How |
|-------|---------------|-----|
| Tool wrappers (unit) | Parser correctness | Fixture of real captured tool output → assert expected `Finding[]`. Adding a tool = adding fixture + parser test. |
| Allowlist guard (unit) | Safety | Table-driven per wrapper: in-list passes; out-of-list rejects + logs; malformed args reject. **Highest-priority safety test.** |
| Faithfulness guard (unit) | Write-up integrity | Synthetic state + tampered write-up (added fabricated command) → assert fail with diff. |
| Graph routing (unit) | Verify node logic | Candidate flag → HumanConfirm; thin findings → Recon; budget exceeded → HumanConfirm("budget-exceeded"); etc. |
| End-to-end (opt-in) | Plumbing on real LLM | Tiny local CTF harness (docker-compose): one known SQLi challenge, one known recon challenge, flag baked in. `@pytest.mark.e2e`, not in default CI. Threshold-based (e.g., 3/5 runs find the flag) — not strict pass/fail. |

LLM-driven nodes (Hypothesize, polish) are **not** snapshot-tested — too brittle. Exercised only via e2e.

## 7. Project Layout

```
AICTFSolver/
  pyproject.toml
  README.md
  design.md
  src/aictfsolver/
    __init__.py
    cli.py                    # entrypoint: aictfsolver run <challenge.yaml>
    state.py                  # AgentState, Finding, Hypothesis, Attempt, LogEntry
    graph.py                  # LangGraph wiring: nodes + edges
    nodes/
      triage.py
      recon.py
      hypothesize.py
      exploit.py
      verify.py
      human_confirm.py
      writeup.py
    tools/
      registry.py             # ToolSpec, register(), get()
      runner.py               # docker exec wrapper, allowlist + timeout enforcement
      parsers/                # one file per tool: nmap.py, sqlmap.py, ...
      specs/                  # one ToolSpec per tool, registered at import
    docker/
      Dockerfile              # ctf-agent-runner image
      entrypoint.sh
    writeup/
      assembler.py            # deterministic section assembly
      polish.py               # LLM polish pass
      faithfulness.py         # guard: every fenced block must exist in trace
  tests/
    unit/
    fixtures/
    e2e/
      targets/                # docker-compose challenge targets
  runs/                       # gitignored; per-run artifacts
  challenges/                 # user-authored ChallengeSpec YAML files
```

`ChallengeSpec` is user-authored YAML per challenge: description, target(s), `allowed_targets`, `flag_format`, category hint, `dangerous_tools_allowed`, optional `budget` overrides.

## 8. Out of Scope for v1

- Crypto, forensics/stego, RE, pwn categories
- Multi-challenge orchestration / CTF event mode
- Submission-endpoint integration (flag confirmation is human-in-the-loop)
- HTML/PDF write-up rendering
- Web UI — CLI only

## 9. Open Questions

- LLM model choice for Hypothesize vs polish (likely different — Hypothesize needs strong reasoning; polish can be cheaper).
- Whether to persist a cross-run "lessons learned" memory, or keep each run hermetic. v1 keeps runs hermetic; revisit after a few real runs.
