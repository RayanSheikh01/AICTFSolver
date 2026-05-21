from aictfsolver.state import Finding
import re

def parse_whatweb_output(stdout, stderr, exit_code):

    regex = re.compile(r"(\w[\w-]*)\[([^\]]+)\]")
    findings = []
    for match in regex.finditer(stdout):
        key = match.group(1)
        value = match.group(2)
        if key == "HTTPServer":
            findings.append(
                Finding(
                    source_tool="whatweb", kind="server", value=value, confidence=0.9
                )
            )
        elif key == "X-Powered-By":
            findings.append(
                Finding(
                    source_tool="whatweb",
                    kind="powered_by",
                    value=value,
                    confidence=0.9,
                )
            )
        elif key == "Title":
            findings.append(
                Finding(
                    source_tool="whatweb", kind="title", value=value, confidence=0.9
                )
            )
        elif key == "IP":
            findings.append(
                Finding(source_tool="whatweb", kind="ip", value=value, confidence=0.9)
            )

    return findings
