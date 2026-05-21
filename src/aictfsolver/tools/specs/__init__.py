from aictfsolver.tools.registry import ToolRegistry

from .nmap import install as install_nmap
from .whatweb import install as install_whatweb
from .curl_headers import install as install_curl_headers

registry = ToolRegistry()
def install_all(): 
    install_nmap(registry)
    install_whatweb(registry)
    install_curl_headers(registry)