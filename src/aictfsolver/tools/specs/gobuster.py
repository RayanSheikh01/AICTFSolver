# ["gobuster","dir","-u","{target}","-w","{wordlist}","-q"], default wordlist /usr/share/wordlists/dirb/common.txt, timeout 300s.

from pydantic import BaseModel

from aictfsolver.tools.parsers.gobuster import parse_gobuster_output

from aictfsolver.tools.registry import ToolRegistry, ToolSpec

class GobusterArgs(BaseModel):
    wordlist: str = "/usr/share/wordlists/dirb/common.txt"
    timeout: int = 300
    
gobuster_spec = ToolSpec(
    name="gobuster",
    category="recon",
    args_schema=GobusterArgs,
    docker_image="gobuster:latest",
    command_template=["gobuster", "dir", "-u", "{target}", "-w", "{wordlist}", "-q"],
    parser=parse_gobuster_output,
    default_timeout_s=300,
    dangerous=False,
)

def install(registry):
    registry.register_tool(gobuster_spec)
    
    