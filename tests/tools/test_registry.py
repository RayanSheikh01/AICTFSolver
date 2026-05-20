import pytest




def test_registry():
    from aictfsolver.state import Finding
    from aictfsolver.tools.registry import ToolRegistry, ToolSpec
    from pydantic import BaseModel

    registry = ToolRegistry()
    assert len(registry.tools) == 0

    class DummyArgs(BaseModel):
        arg1: str
        arg2: int
    def dummy_parser(output: str, raw_log_path: str, exit_code: int) -> list[Finding]:
        return []
    
    tool_spec = ToolSpec(
        name="dummy_tool",
        category="utility",
        args_schema=DummyArgs,
        docker_image="dummy/image:latest",
        command_template=["dummy_tool", "--arg1", "{arg1}", "--arg2", "{arg2}"],
        parser=dummy_parser,
        default_timeout_s=60,
        dangerous=False
    )
    registry.register_tool(tool_spec)
    assert len(registry.tools) == 1
    retrieved_spec = registry.get_tool("dummy_tool")
    assert retrieved_spec.name == tool_spec.name
    assert retrieved_spec.category == tool_spec.category
    assert retrieved_spec.docker_image == tool_spec.docker_image
    assert retrieved_spec.command_template == tool_spec.command_template
    assert retrieved_spec.default_timeout_s == tool_spec.default_timeout_s
    assert retrieved_spec.dangerous == tool_spec.dangerous
    with pytest.raises(ValueError):
        registry.register_tool(tool_spec)
    with pytest.raises(ValueError):
        registry.get_tool("non_existent_tool")
    registry.reset()
    assert len(registry.tools) == 0

