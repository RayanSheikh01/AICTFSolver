# AI CTF Solver Agent — Implementation Plan (Lean)

**Goal:** Autonomous LangGraph agent that solves Web/Recon CTF challenges in a sandboxed Docker container and emits a publishable write-up.

**Tech:** Python 3.11+, LangGraph, Anthropic SDK, Pydantic v2, Docker, pytest, PyYAML.

See [design.md](design.md) for rationale.

**Root:** `c:\Users\LenSD\Documents\Rayan\Career\Programs\AICTFSolver\`

All paths below are relative to root. Each task lists files to create/modify and a minimal sketch of the key code; fill in details from the design doc and signatures shown.

---

## Task 1 — Scaffold

**Create:**
- `pyproject.toml`
- `src/aictfsolver/__init__.py`
- `tests/__init__.py`
- `.gitignore`
- `README.md`

`pyproject.toml` deps: `langgraph`, `anthropic`, `pydantic>=2`, `pyyaml`, `docker`, `click`. Dev: `pytest`, `ruff`. Entry point: `aictfsolver = "aictfsolver.cli:main"`. Pytest marker `e2e` deselected by default (`addopts = "-m 'not e2e'"`).

`.gitignore`: `__pycache__/`, `.venv/`, `runs/`, `.pytest_cache/`, `*.egg-info/`, `.env`.

Then: `pip install -e ".[dev]"` and `git init` + first commit.

---

## Task 2 — Core State Types

**Create:**
- `src/aictfsolver/state.py`
- `tests/unit/test_state.py`

Define (Pydantic models unless noted):

- `BudgetCounters` — `iterations_used/max`, `tool_calls_used/max`, `wall_clock_s_used/max`; `.exceeded() -> bool`.
- `ChallengeSpec` — `description`, `target`, `flag_format` (regex), `allowed_targets: list[str]` (validator: non-empty), `category_hint` ∈ {`web`,`network`,`unknown`}, `dangerous_tools_allowed: list[str]`, `budget: BudgetCounters`.
- `Finding` — `source_tool`, `kind`, `value`, `confidence`.
- `Hypothesis` — `id`, `text`, `rank`, `status` ∈ {`open`,`tried`,`disproved`,`confirmed`}, `basis`.
- `Attempt` — `hypothesis_id`, `tool`, `args`, `exit_code`, `summary`, `raw_log_path`.
- `LogEntry` — `node`, `ts`, `kind` ∈ {`thought`,`command`,`output`,`decision`}, `content`.
- `HumanTurn` — `kind` ∈ {`confirm_request`,`confirm`,`reject`}, `payload`.
- `AgentState` (TypedDict) — wires all of the above plus `phase`, `candidate_flags`, `human_messages`.
- `new_state(spec) -> AgentState` — initializes empty collections, `phase="triage"`, copies budget.

**Tests:** allowlist empty → raises; `new_state` returns empty collections + `phase=="triage"`.

---

## Task 3 — YAML Loader

**Create:**
- `src/aictfsolver/config.py`
- `challenges/example.yaml`
- `tests/unit/test_config.py`

```python
# config.py
def load_challenge(path: Path) -> ChallengeSpec:
    return ChallengeSpec.model_validate(yaml.safe_load(Path(path).read_text()))
```

`example.yaml`: fill in description, target, flag_format regex, allowed_targets, category_hint.

---

## Task 4 — Tool Registry

**Create:**
- `src/aictfsolver/tools/__init__.py` (empty)
- `src/aictfsolver/tools/registry.py`
- `tests/unit/tools/__init__.py` (empty)
- `tests/unit/tools/test_registry.py`

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    category: Literal["recon","exploit","utility"]
    args_schema: type[BaseModel]
    docker_image: str             # "local" bypasses docker
    command_template: list[str]   # tokens with {name} placeholders
    parser: Callable[[str,str,int], list[Finding]]
    default_timeout_s: int
    dangerous: bool = False

_REGISTRY: dict[str, ToolSpec] = {}
def register(spec): ...           # raise on duplicate
def get(name): ...                # raise on missing
def all_tools(): ...
def _reset_for_tests(): _REGISTRY.clear()
```

**Tests:** register + get; duplicate raises; missing raises.

---

## Task 5 — Allowlist Guard (safety-critical)

**Create:**
- `src/aictfsolver/tools/allowlist.py`
- `tests/unit/tools/test_allowlist.py`

```python
class AllowlistViolation(Exception): ...

def check_target(candidate: str, allowed: list[str]) -> None:
    # 1. extract hostname (parse URL if scheme present; else bare host[:port])
    # 2. reject empty / whitespace / control chars / suffix tricks
    # 3. for each rule: try ipaddress.ip_network(rule) — CIDR match;
    #    else exact (case-insensitive) hostname match. No suffix match.
    # 4. no match → raise AllowlistViolation
```

**Tests (parametrized):** allowlist `["target.local","10.0.0.0/24"]`. Pass: `target.local`, `http://target.local:8080/x`, `10.0.0.5`. Reject: `evil.example.com`, `10.0.1.5`, `target.local.evil.com` (suffix trick), `evil.com#target.local`, empty, malformed.

---

## Task 6 — Dockerfile

**Create:**
- `src/aictfsolver/docker/Dockerfile`
- `src/aictfsolver/docker/entrypoint.sh`

Base `kalilinux/kali-rolling`. Install: `nmap sqlmap gobuster nikto whatweb hydra hashcat curl python3 python3-pip python3-requests iproute2`. pip install `pwntools`. `WORKDIR /work`. Entrypoint creates `/work/raw` then `exec "$@"`. Default CMD `sleep infinity`.

Build: `docker build -t ctf-agent-runner:latest src/aictfsolver/docker/`
Smoke: `docker run --rm ctf-agent-runner:latest nmap --version`.

---

## Task 7 — Docker Runner

**Create:**
- `src/aictfsolver/tools/runner.py`
- `tests/unit/tools/test_runner.py`

```python
@dataclass
class ToolResult:
    exit_code: int; stdout: str; stderr: str
    findings: list[Finding]; raw_log_path: str

class ContainerRunner:
    def __init__(self, container_id, work_dir): ...
    @classmethod
    def start(cls, image, work_dir, allowed_targets) -> "ContainerRunner":
        # docker run -d --rm --name ctf-<uuid> -v <work>:/work
        #   --cpus 2 --memory 2g --tmpfs /tmp <image>
        ...
    def stop(self): ...           # docker stop

    def run_tool(self, name: str, args: dict, state: AgentState) -> ToolResult:
        spec = get_tool(name)
        # 1. budget check → raise RuntimeError("budget...")
        # 2. dangerous gate → PermissionError if not in state.challenge.dangerous_tools_allowed
        # 3. validate args via spec.args_schema
        # 4. allowlist: for any arg key == "target" or *_target → check_target(...)
        # 5. format command_template tokens
        # 6. if spec.docker_image == "local": dispatch _LOCAL_HANDLERS[name]
        #    else: self._docker_exec(cmd, timeout)
        # 7. write raw log to work_dir/raw/<name>-NNN.log
        # 8. parse with spec.parser; append Attempt + LogEntry(command,output)
        # 9. bump loop_budget.tool_calls_used + wall_clock_s_used
        # 10. return ToolResult
        ...

    def _docker_exec(self, cmd, timeout) -> tuple[int, bytes, bytes]:
        # subprocess.run(["docker","exec",container,*cmd], capture_output=True, timeout=...)
        ...

_LOCAL_HANDLERS: dict[str, Callable] = {}
def register_local(name, fn): _LOCAL_HANDLERS[name] = fn
```

**Tests (mock `_docker_exec`):** out-of-allowlist → `AllowlistViolation`; valid run parses output, increments budget, calls docker exec with formatted command; budget-exceeded → `RuntimeError`; dangerous without opt-in → `PermissionError`.

---

## Task 8 — nmap Tool

**Create:**
- `src/aictfsolver/tools/parsers/__init__.py` (empty)
- `src/aictfsolver/tools/parsers/nmap.py`
- `src/aictfsolver/tools/specs/__init__.py`
- `src/aictfsolver/tools/specs/nmap.py`
- `tests/fixtures/nmap_basic.txt`
- `tests/unit/tools/parsers/__init__.py` (empty)
- `tests/unit/tools/parsers/test_nmap.py`

Parser: regex `^(\d+/\w+)\s+open\s+(\S+)(?:\s+(.*))?$` per line → `Finding(source_tool="nmap", kind="open_port", value=f"{port} {svc} {ver}")`.

Spec: `command_template=["nmap","-sV","-p","{ports}","{target}"]`, args `target` + `ports="1-1000"`, timeout 120s.

`specs/__init__.py`:
```python
from . import nmap as _nmap
def install_all(): _nmap.install()
```

Fixture: paste real nmap output containing ports 22/ssh, 80/http, 443/ssl-http.

---

## Task 9 — Remaining Recon Tools

For each tool below, create 4 files following the Task 8 pattern, register in `specs/__init__.py`, and add a parser test using a real-output fixture.

### 9a. whatweb
- `src/aictfsolver/tools/parsers/whatweb.py` — regex `(\w[\w-]*)\[([^\]]+)\]`; map keys `HTTPServer→server`, `X-Powered-By→powered_by`, `Title→title`, `IP→ip`.
- `src/aictfsolver/tools/specs/whatweb.py` — command `["whatweb","{target}"]`, timeout 60s.
- `tests/fixtures/whatweb_basic.txt`, `tests/unit/tools/parsers/test_whatweb.py`.

### 9b. curl_headers
- `src/aictfsolver/tools/parsers/curl_headers.py` — first line `HTTP/x.y NNN` → status; subsequent `Key: Value` lines → `kind="header"`.
- `src/aictfsolver/tools/specs/curl_headers.py` — `["curl","-sSI","{target}"]`, timeout 30s.
- `tests/fixtures/curl_headers_basic.txt`, `tests/unit/tools/parsers/test_curl_headers.py`.

### 9c. gobuster
- `src/aictfsolver/tools/parsers/gobuster.py` — regex `^(/\S+)\s+\(Status:\s*(\d+)\)`; emit `kind="path"`.
- `src/aictfsolver/tools/specs/gobuster.py` — `["gobuster","dir","-u","{target}","-w","{wordlist}","-q"]`, default wordlist `/usr/share/wordlists/dirb/common.txt`, timeout 300s.
- `tests/fixtures/gobuster_basic.txt`, `tests/unit/tools/parsers/test_gobuster.py`.

### 9d. nikto
- `src/aictfsolver/tools/parsers/nikto.py` — lines starting `+ ` containing `:` → `kind="issue"`. Skip metadata keys (`Target IP`, `Target Hostname`, `Target Port`, `Server`, `Start Time`, `End Time`).
- `src/aictfsolver/tools/specs/nikto.py` — `["nikto","-h","{target}"]`, timeout 600s.
- `tests/fixtures/nikto_basic.txt`, `tests/unit/tools/parsers/test_nikto.py`.

After each: `register(...)` import in `specs/__init__.py`.

---

## Task 10 — Exploit Tools

### 10a. sqlmap
**Create:**
- `src/aictfsolver/tools/parsers/sqlmap.py` — match `parameter '(\S+)' is .*injectable` → `kind="injection"`; `back-end DBMS is (\S+)` → `kind="dbms"`; `parameter '(\S+)' is vulnerable` → `kind="injection"`.
- `src/aictfsolver/tools/specs/sqlmap.py` — `["sqlmap","-u","{target}","--batch","--level=2"]`, args `target` + optional `data`, timeout 600s.
- `tests/fixtures/sqlmap_injectable.txt`, `tests/fixtures/sqlmap_clean.txt`, `tests/unit/tools/parsers/test_sqlmap.py`.

### 10b. curl_exploit
**Create:**
- `src/aictfsolver/tools/parsers/curl_exploit.py` — split on `\r\n\r\n` or `\n\n`; first line of head → `kind="status"`; body → `kind="body"` (truncate to 2000 chars).
- `src/aictfsolver/tools/specs/curl_exploit.py` — `["curl","-isS","-X","{method}","{target}"]`, args `target` + `method="GET"` + optional `data`/`header`, timeout 30s.
- `tests/unit/tools/parsers/test_curl_exploit.py`.

### 10c. hydra (dangerous=True)
**Create:**
- `src/aictfsolver/tools/parsers/hydra.py` — regex `login:\s*(\S+)\s+password:\s*(\S+)` → `Finding(kind="credential", value=f"{u}:{p}")`.
- `src/aictfsolver/tools/specs/hydra.py` — `["hydra","-L","{userlist}","-P","{passlist}","-t","4","{target}","{service}","{form}"]`, args `target`, `service`, `form`, `userlist`, `passlist`. **`dangerous=True`**, timeout 900s.
- `tests/fixtures/hydra_success.txt`, `tests/unit/tools/parsers/test_hydra.py`.

Register each in `specs/__init__.py`.

---

## Task 11 — Utility Tools (in-process)

**Create:**
- `src/aictfsolver/tools/specs/flag_scan.py` — args `text`; handler regex-finds `state.challenge.flag_format` matches, joins with `\n`. Parser splits stdout into `Finding(kind="candidate_flag")` per line.
- `src/aictfsolver/tools/specs/decode.py` — args `text`, `encoding` ∈ {`base64`,`url`,`hex`}; handler decodes. Parser → single `Finding(kind="decoded")`.
- `src/aictfsolver/tools/specs/regex_extract.py` — args `text`, `pattern`; handler returns `\n`-joined `re.findall` matches. Parser → `Finding(kind="match")` per line.

Each uses `docker_image="local"` and calls `register_local(name, handler)`. Tests under `tests/unit/tools/` covering each handler.

Register all in `specs/__init__.py`.

---

## Task 12 — LLM Client

**Create:**
- `src/aictfsolver/llm.py`
- `tests/unit/test_llm.py`

```python
@lru_cache(maxsize=1)
def _client() -> Anthropic: return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def ask(system: str, user: str, *, model="claude-sonnet-4-6", max_tokens=2048) -> str:
    resp = _client().messages.create(model=model, max_tokens=max_tokens,
        system=system, messages=[{"role":"user","content":user}])
    return "".join(b.text for b in resp.content if hasattr(b, "text"))

MODEL_HYPOTHESIZE = "claude-opus-4-7"
MODEL_POLISH = "claude-sonnet-4-6"
```

**Test:** patch `_client` to a MagicMock; assert `ask` forwards `system`/`messages`/`model`.

---

## Task 13 — Triage Node

**Create:**
- `src/aictfsolver/nodes/__init__.py` (empty)
- `src/aictfsolver/nodes/triage.py`
- `tests/unit/nodes/__init__.py` (empty)
- `tests/unit/nodes/test_triage.py`

`triage(state)`: append `Finding(kind="target")` + `Finding(kind="category")` from `ChallengeSpec`; append a `LogEntry(node="triage", kind="decision")`; set `phase="recon"`. Pure function, no LLM.

---

## Task 14 — Recon Node

**Create:**
- `src/aictfsolver/nodes/recon.py`
- `tests/unit/nodes/test_recon.py`

`recon(state, runner)`:
1. Build system prompt: "CTF recon planner — pick 1-3 tools, JSON `{"tools":[{"name","args"}]}`."
2. Include a registry blurb (recon + utility tools only, with arg-schema field names).
3. `ask(...)` with `MODEL_HYPOTHESIZE`; log reply as `thought`.
4. `json.loads(reply)`, iterate first 3 tools, `runner.run_tool(name, args, state)`; catch exceptions → log `decision`.
5. `state["loop_budget"].iterations_used += 1`; `phase="hypothesize"`.

**Test:** mock `ask` to return a 2-tool plan; mock `runner.run_tool` to return findings; assert `run_tool` called twice, findings appended, `phase=="hypothesize"`.

---

## Task 15 — Hypothesize Node

**Create:**
- `src/aictfsolver/nodes/hypothesize.py`
- `tests/unit/nodes/test_hypothesize.py`

`hypothesize(state)`: LLM-only. Prompt: "Given findings + already-tried hypotheses, propose 1-3 ranked. JSON `{"hypotheses":[{"text","rank","basis"}]}`." Append each as `Hypothesis(id=uuid4()[:8], status="open")`. `phase="exploit"`. Log raw reply as `thought`.

---

## Task 16 — Exploit Node

**Create:**
- `src/aictfsolver/nodes/exploit.py`
- `tests/unit/nodes/test_exploit.py`

`exploit(state, runner)`:
1. Pick top `status=="open"` hypothesis by `rank`. If none → `phase="verify"`, return.
2. Prompt: "Translate this hypothesis into a SINGLE tool call. JSON `{"tool","args"}`." Include exploit + utility tool registry blurb (mark `[DANGEROUS]`).
3. `ask(...)`, log `thought`, parse.
4. `runner.run_tool(...)`; on success, extend findings, link last `Attempt.hypothesis_id = top.id`, mark `top.status="tried"`. On exception, log `decision`, still mark `tried`.
5. `phase="verify"`.

---

## Task 17 — Verify Node (routing brain — table-driven tests)

**Create:**
- `src/aictfsolver/nodes/verify.py`
- `tests/unit/nodes/test_verify.py`

```python
THIN_FINDINGS_THRESHOLD = 3

def verify(state):
    pat = re.compile(state["challenge"].flag_format)
    blobs = [f.value for f in state["findings"]] + [a.summary for a in state["attempts"]]
    for c in dict.fromkeys(m for b in blobs for m in pat.findall(b)):
        state["candidate_flags"].append(c)

    if state["candidate_flags"]:
        state["human_messages"].append(HumanTurn("confirm_request", f"...{state['candidate_flags']}"))
        state["phase"] = "human_confirm"; return state
    if state["loop_budget"].exceeded():
        state["human_messages"].append(HumanTurn("confirm_request", "budget exceeded"))
        state["phase"] = "human_confirm"; return state
    if any(h.status == "open" for h in state["hypotheses"]):
        state["phase"] = "exploit"; return state
    state["phase"] = "recon" if len(state["findings"]) < THIN_FINDINGS_THRESHOLD else "hypothesize"
    return state
```

**Tests:** candidate flag in finding → `human_confirm`; thin findings + all `tried` → `recon`; rich findings + all `tried` → `hypothesize`; budget exceeded → `human_confirm` with `confirm_request` containing "budget".

---

## Task 18 — HumanConfirm Node

**Create:**
- `src/aictfsolver/nodes/human_confirm.py`
- `tests/unit/nodes/test_human_confirm.py`

`human_confirm(state, input_fn=input)`:
- Prompt user with candidate flags. Accept `y` (confirm first candidate), `n` (reject all + mark all `tried` → `disproved` + clear candidates + `phase="hypothesize"`), or a string matching `flag_format` (override + confirm).
- Append `HumanTurn` accordingly; log `decision`.

**Tests:** pass `input_fn` lambda returning `"y"`, `"n"`, and a literal flag string.

---

## Task 19 — Write-up Assembler

**Create:**
- `src/aictfsolver/writeup/__init__.py` (empty)
- `src/aictfsolver/writeup/assembler.py`
- `tests/unit/writeup/__init__.py` (empty)
- `tests/unit/writeup/test_assembler.py`

`assemble(state) -> list[tuple[str,str]]` returning sections in order:
1. **Challenge Overview** — target, category, description.
2. **Reconnaissance** — recon-node log entries + recon findings list.
3. **Analysis** — all hypotheses sorted by rank with status + basis.
4. **Exploitation** — for each `tried`/`confirmed` hypothesis, its linked `Attempt`s as fenced code blocks `$ tool args` + summary.
5. **Flag Recovery** — first candidate flag in backticks (or "_no flag captured_").
6. **Dead Ends** — bullet list of `disproved` hypotheses.

**Test:** craft state with one `confirmed` + one `disproved` hypothesis + one attempt + one candidate flag → assert all 6 section titles present, "Dead Ends" mentions the disproved hypothesis.

---

## Task 20 — Polish

**Create:**
- `src/aictfsolver/writeup/polish.py`
- `tests/unit/writeup/test_polish.py`

`polish_sections(sections) -> list[tuple[str,str]]`: one `ask()` per section with `MODEL_POLISH`. System prompt: "Polish into markdown. PRESERVE fenced code blocks and commands verbatim — do NOT invent steps." Returns same titles, polished bodies.

**Test:** patch `ask` → identity-ish; assert one call per section, titles preserved.

---

## Task 21 — Faithfulness Guard

**Create:**
- `src/aictfsolver/writeup/faithfulness.py`
- `tests/unit/writeup/test_faithfulness.py`

```python
class FaithfulnessViolation(Exception): ...
_FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)

def check_faithfulness(markdown, state):
    trace = "\n".join([a.tool for a in state["attempts"]]
                    + [str(a.args) for a in state["attempts"]]
                    + [a.summary for a in state["attempts"]]
                    + [e.content for e in state["reasoning_log"]])
    for block in _FENCE.findall(markdown):
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"): continue
            stripped = line[2:] if line.startswith("$ ") else line
            if line not in trace and stripped not in trace:
                raise FaithfulnessViolation(f"fenced line not in trace: {line!r}")
```

**Tests:** matching command passes; tampered command (e.g., `rm -rf /`) raises with the bogus line in the message.

---

## Task 22 — Writeup Node

**Create:**
- `src/aictfsolver/nodes/writeup.py`
- `tests/unit/nodes/test_writeup.py`

`writeup(state, run_dir: Path) -> Path`:
1. `sections = assemble(state)`
2. `polished = polish_sections(sections)`
3. Build markdown: YAML frontmatter (`title`, `category`, `tools_used`, `duration_seconds`, `generated_at`) + each section as `## Title\n\nbody` + "Tools & Commands Reference" appendix listing each `Attempt`.
4. `check_faithfulness(md, state)`.
5. Write `run_dir/writeup.md`. Set `phase="done"`. Return path.

**Test:** patch `polish_sections` to identity; assert file exists and contains the candidate flag + "Reconnaissance" header.

---

## Task 23 — Graph Wiring

**Create:**
- `src/aictfsolver/graph.py`
- `tests/unit/test_graph.py`

```python
def build_graph(runner, run_dir):
    g = StateGraph(AgentState)
    g.add_node("triage", lambda s: triage(s))
    g.add_node("recon", lambda s: recon(s, runner))
    g.add_node("hypothesize", hypothesize)
    g.add_node("exploit", lambda s: exploit(s, runner))
    g.add_node("verify", verify)
    g.add_node("human_confirm", human_confirm)
    g.add_node("writeup", lambda s: (writeup(s, Path(run_dir)), s)[1])
    g.set_entry_point("triage")
    g.add_edge("triage","recon"); g.add_edge("recon","hypothesize")
    g.add_edge("hypothesize","exploit"); g.add_edge("exploit","verify")
    g.add_conditional_edges("verify", lambda s: s["phase"],
        {"hypothesize":"hypothesize","exploit":"exploit","recon":"recon",
         "human_confirm":"human_confirm"})
    g.add_conditional_edges("human_confirm", lambda s: s["phase"],
        {"writeup":"writeup","hypothesize":"hypothesize"})
    g.add_edge("writeup", END)
    return g.compile()
```

---

## Task 24 — CLI

**Create:**
- `src/aictfsolver/cli.py`
- `tests/unit/test_cli.py`

Click app with `run <spec.yaml>` command:
1. `install_all()` (registers tools).
2. `load_challenge(path)`.
3. Make `run_dir = runs/<run-id>/`.
4. `with _runner_context(image, run_dir, spec.allowed_targets) as runner:` — context manager wraps `ContainerRunner.start` / `.stop`.
5. `graph = build_graph(runner, run_dir)`; `graph.invoke(new_state(spec))`.
6. Print final phase + writeup path.

**Test:** patch `build_graph` and `_runner_context` with MagicMocks; `CliRunner().invoke(main, ["run", spec])` returns exit 0.

---

## Task 25 — E2E Harness (opt-in, `@pytest.mark.e2e`)

**Create:**
- `tests/e2e/__init__.py` (empty)
- `tests/e2e/targets/docker-compose.yaml`
- `tests/e2e/targets/sqli/Dockerfile`
- `tests/e2e/targets/sqli/app.py` — Flask, vulnerable SQLite `WHERE id={uid}`, baked flag `flag{e2e_sqli_demo}` for admin.
- `tests/e2e/test_sqli_challenge.py` — fixture brings up compose; runs `build_graph` 5× against the target with a small budget; asserts ≥3 runs surface `flag{` in `candidate_flags`. Skips default `pytest`; opt-in via `pytest -m e2e`.

---

## Task 26 — Final Smoke + README

**Modify:**
- `README.md` — install, build Docker image, write a `ChallengeSpec` YAML, run `aictfsolver run challenges/example.yaml`, where artifacts go, opt-in e2e command.

Then: `pytest -v` (all unit pass), optional manual run with `ANTHROPIC_API_KEY`, `git tag v0.1.0`.

---

## Coverage check

- State + types: T2. Loader: T3. Registry: T4. Allowlist (safety): T5. Docker image + runner: T6–T7. Recon tools: T8–T9. Exploit tools: T10. Utility tools: T11. LLM: T12. Nodes: T13–T18, T22. Write-up pipeline: T19–T21. Graph: T23. CLI: T24. E2E: T25. Docs: T26.
- All design.md sections mapped; out-of-scope items (crypto/RE/pwn, submission API, HTML rendering) intentionally absent.
