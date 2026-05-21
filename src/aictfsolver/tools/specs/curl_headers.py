# ["curl","-sSI","{target}"], timeout 30s.

from pydantic import BaseModel

from aictfsolver.state import Finding
from aictfsolver.tools.parsers.curl_headers import parse_curl_headers_output
from aictfsolver.tools.registry import ToolRegistry, ToolSpec

class CurlHeadersArgs(BaseModel):
    timeout: int = 30
    
curl_headers_spec = ToolSpec(
    name="curl_headers",
    category="recon",
    args_schema=CurlHeadersArgs,
    docker_image="curl:latest",
    command_template=["curl", "-sSI", "{target}"],
    parser=parse_curl_headers_output,
    default_timeout_s=30,
    dangerous=False,
)

def install(registry):
    registry.register_tool(curl_headers_spec)