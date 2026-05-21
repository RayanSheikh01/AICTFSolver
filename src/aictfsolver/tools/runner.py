import os

import pydantic

from aictfsolver.state import Finding
from aictfsolver.tools.registry import ToolRegistry, ToolSpec


class ToolResult:
    exit_code: int
    stdout: str
    stderr: str
    findings: list[Finding]
    raw_log_path: str

    def __init__(self, exit_code, stdout, stderr, findings, raw_log_path):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.findings = findings
        self.raw_log_path = raw_log_path


class ContainerRunner:
    def __init__(self, container_id, work_dir, registry: ToolRegistry | None = None):
        self.container_id = container_id
        self.work_dir = work_dir
        self.registry = registry if registry is not None else ToolRegistry()
        self.container = None

    def start(self, image, work_dir, allowed_targets):
        import docker

        self.client = docker.from_env()
        self.container = self.client.containers.run(
            image=image,
            command="sleep infinity",
            working_dir=work_dir,
            volumes={work_dir: {"bind": "/work", "mode": "rw"}},
            detach=True,
        )

    def stop(self):
        self.container.stop()
        self.container.remove()

    def run_tool(self, name, args, state) -> ToolResult:
        spec = state["spec"]

        # 1. budget check
        if spec.budget.tool_calls_used >= spec.budget.tool_calls_max:
            raise RuntimeError("Tool call budget exceeded")

        tool_spec = self.registry.get_tool(name)

        # 2. dangerous-tool gate
        if tool_spec.dangerous and name not in spec.dangerous_tools_allowed:
            raise RuntimeError(f"Tool {name} is not allowed in this challenge")

        # 3. validate args
        try:
            parsed_args = tool_spec.args_schema.model_validate(args)
        except pydantic.ValidationError as e:
            raise RuntimeError(f"Invalid arguments for tool {name}: {e}")

        # 4. allowlist check — TODO: wire AllowlistViolation for target/*_target args

        # 5. render command
        command = []
        for part in tool_spec.command_template:
            if part.startswith("{") and part.endswith("}"):
                arg_name = part[1:-1]
                command.append(str(getattr(parsed_args, arg_name)))
            else:
                command.append(part)

        # 6. execute in container
        exec_result = self.container.exec_run(
            command, workdir="/work", stdout=True, stderr=True
        )
        exit_code = exec_result.exit_code
        stdout = exec_result.output.decode("utf-8")
        stderr = ""

        # 7. write raw log under work_dir/raw/
        raw_dir = os.path.join(self.work_dir, "raw")
        os.makedirs(raw_dir, exist_ok=True)
        raw_log_path = os.path.join(
            raw_dir, f"{name}-{spec.budget.tool_calls_used:03d}.log"
        )
        with open(raw_log_path, "w") as f:
            f.write(stdout)

        findings = tool_spec.parser(stdout, stderr, exit_code)

        # 8. bump budget
        spec.budget.tool_calls_used += 1

        return ToolResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            findings=findings,
            raw_log_path=raw_log_path,
        )
