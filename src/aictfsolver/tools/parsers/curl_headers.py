
from aictfsolver.state import Finding
import re

def parse_curl_headers_output(stdout, stderr, exit_code):
    lines = stdout.splitlines()
    findings = []
    if not lines:
        return findings

    # Parse status line
    status_line = lines[0]
    match = re.match(r"HTTP/\d+\.\d+\s+(\d+)", status_line)
    if match:
        status_code = match.group(1)
        findings.append(Finding(source_tool="curl_headers", kind="status", value=status_code, confidence=0.9))

    # Parse headers
    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            findings.append(Finding(source_tool="curl_headers", kind=f"header_{key.lower()}", value=value, confidence=0.9))

    return findings

