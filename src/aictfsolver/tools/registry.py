from typing import Callable, Dict, Literal

from aictfsolver.state import Finding
from pydantic import BaseModel

class ToolSpec:
    name: str
    category: Literal["recon", "exploit", "utility"]
    args_schema: type[BaseModel]
    docker_image: str
    command_template: list[str]
    parser: Callable[[str, str, int], list[Finding]]
    default_timeout_s: int
    dangerous: bool = False

    def __init__(self, name: str, category: Literal["recon", "exploit", "utility"], args_schema: type[BaseModel],
                 docker_image: str, command_template: list[str], parser: Callable[[str, str, int], list[Finding]], default_timeout_s: int, dangerous: bool = False):
        self.name = name
        self.category = category
        self.args_schema = args_schema
        self.docker_image = docker_image
        self.command_template = command_template
        self.parser = parser
        self.default_timeout_s = default_timeout_s
        self.dangerous = dangerous


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolSpec] = {}
    
    def register_tool(self, tool_spec: ToolSpec):
        if tool_spec.name in self.tools:
            raise ValueError(f"Tool with name {tool_spec.name} is already registered")
        self.tools[tool_spec.name] = tool_spec
    
    def get_tool(self, name: str) -> ToolSpec:
        if name not in self.tools:
            raise ValueError(f"Tool with name {name} is not registered")
        return self.tools[name]
    
    def reset(self):
        self.tools = {}

