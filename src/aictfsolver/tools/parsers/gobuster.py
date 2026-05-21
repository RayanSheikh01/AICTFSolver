import re
from aictfsolver.state import Finding


def parse_gobuster_output(output, stderr, exit_code):
    
    findings = []
    for line in output.splitlines():
        match = re.match(r"^(/\S+)\s+\(Status:\s*(\d+)\)", line)
        if match:
            path = match.group(1)
            status = match.group(2)
            findings.append(Finding(source_tool="gobuster", kind="path", value=f"{path} (status {status})", confidence=0.9))
    return findings








