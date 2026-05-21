from pydantic import BaseModel

from aictfsolver.tools.parsers.whatweb import parse_whatweb_output
from aictfsolver.tools.registry import ToolSpec

class WhatWebArgs(BaseModel):
    timeout: int = 60
        

what_web_spec = ToolSpec(
    name="whatweb",
    category="recon",
    args_schema=WhatWebArgs,
    docker_image="whatweb:latest",  
    command_template=["whatweb", "{target}"],
    parser=parse_whatweb_output,
    default_timeout_s=60,
    dangerous=False,
)

def install(registry):
    registry.register_tool(what_web_spec)
    
