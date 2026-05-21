from aictfsolver.tools.registry import ToolRegistry

from .nmap import install

registry = ToolRegistry()
def install_all(): install(registry)