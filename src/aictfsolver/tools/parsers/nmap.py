from aictfsolver.state import Finding
import re

def parse_nmap_output(stdout, stderr, exit_code):
    
    regex = re.compile(r"^(\d+/\w+)\s+open\s+(\S+)(?:\s+(.*))?$", re.MULTILINE)
    findings = []
    for match in regex.finditer(stdout):
        port = match.group(1)
        svc = match.group(2)
        ver = match.group(3) or ""
        findings.append(Finding(source_tool="nmap", kind="open_port", value=f"{port} {svc} {ver}".strip(), confidence=0.9))
        
    

    return findings