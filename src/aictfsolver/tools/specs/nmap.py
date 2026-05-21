from pydantic import BaseModel

from aictfsolver.state import Finding
from aictfsolver.tools.registry import ToolRegistry, ToolSpec
from aictfsolver.tools.parsers.nmap import parse_nmap_output


class NmapArgs(BaseModel):
    ports: str = "1-1000"
    timeout: int = 120


nmap_spec = ToolSpec(
    name="nmap",
    category="recon",
    args_schema=NmapArgs,
    docker_image="nmap:latest",
    command_template=["nmap", "-sV", "-p", "{ports}", "{target}"],
    parser=parse_nmap_output,
    default_timeout_s=120,
    dangerous=False,
)


def install(registry: ToolRegistry):
    registry.register_tool(nmap_spec)
