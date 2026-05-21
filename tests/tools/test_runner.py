from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from aictfsolver.state import BudgetCounters, ChallengeSpec, new_state
from aictfsolver.tools.registry import ToolRegistry, ToolSpec
from aictfsolver.tools.runner import ContainerRunner, ToolResult


class EchoArgs(BaseModel):
    message: str


def _make_spec(budget=None, dangerous_allowed=None):
    return ChallengeSpec(
        description="Test challenge",
        target="test_target",
        flag_format="flag{.*}",
        allowed_targets=["test_target"],
        category_hint="test_category",
        dangerous_tools_allowed=dangerous_allowed or [],
        budget=budget
        or BudgetCounters(iterations_max=10, tool_calls_max=5, wall_clock_s_max=60.0),
    )


def _make_registry():
    reg = ToolRegistry()
    reg.register_tool(
        ToolSpec(
            name="echo",
            category="utility",
            args_schema=EchoArgs,
            docker_image="local",
            command_template=["echo", "{message}"],
            parser=lambda stdout, stderr, exit_code: [],
            default_timeout_s=10,
        )
    )
    reg.register_tool(
        ToolSpec(
            name="dangerous_tool",
            category="exploit",
            args_schema=EchoArgs,
            docker_image="local",
            command_template=["dangerous"],
            parser=lambda stdout, stderr, exit_code: [],
            default_timeout_s=10,
            dangerous=True,
        )
    )
    return reg


def _make_runner(work_dir, container_output=b"", exit_code=0):
    runner = ContainerRunner(
        container_id="fake", work_dir=str(work_dir), registry=_make_registry()
    )
    fake_exec = MagicMock()
    fake_exec.exit_code = exit_code
    fake_exec.output = container_output
    runner.container = MagicMock()
    runner.container.exec_run.return_value = fake_exec
    return runner


def test_run_tool_valid(tmp_path):
    spec = _make_spec()
    state = new_state(spec)
    runner = _make_runner(tmp_path, container_output=b"Hello, World!\n")

    result = runner.run_tool("echo", {"message": "Hello, World!"}, state)

    assert isinstance(result, ToolResult)
    assert result.exit_code == 0
    assert result.stdout.strip() == "Hello, World!"
    assert spec.budget.tool_calls_used == 1


def test_run_tool_budget_exceeded(tmp_path):
    spec = _make_spec(
        budget=BudgetCounters(
            iterations_max=10,
            tool_calls_used=5,
            tool_calls_max=5,
            wall_clock_s_max=60.0,
        )
    )
    state = new_state(spec)
    runner = _make_runner(tmp_path)

    with pytest.raises(RuntimeError, match="Tool call budget exceeded"):
        runner.run_tool("echo", {"message": "hi"}, state)


def test_run_tool_dangerous_not_allowed(tmp_path):
    spec = _make_spec()
    state = new_state(spec)
    runner = _make_runner(tmp_path)

    with pytest.raises(
        RuntimeError, match="Tool dangerous_tool is not allowed in this challenge"
    ):
        runner.run_tool("dangerous_tool", {"message": "x"}, state)


def test_run_tool_dangerous_allowed_when_opted_in(tmp_path):
    spec = _make_spec(dangerous_allowed=["dangerous_tool"])
    state = new_state(spec)
    runner = _make_runner(tmp_path, container_output=b"ok\n")

    result = runner.run_tool("dangerous_tool", {"message": "x"}, state)

    assert result.exit_code == 0
    assert spec.budget.tool_calls_used == 1


def test_run_tool_invalid_args(tmp_path):
    spec = _make_spec()
    state = new_state(spec)
    runner = _make_runner(tmp_path)

    with pytest.raises(RuntimeError, match="Invalid arguments for tool echo:"):
        runner.run_tool("echo", {"invalid_arg": "value"}, state)
