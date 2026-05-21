import pytest

from aictfsolver.tools.parsers.gobuster import parse_gobuster_output

def test_gobuster_parser():
    with open("tests/fixtures/gobuster_basic.txt") as f:
        gobuster_output = f.read()

    findings = parse_gobuster_output(gobuster_output, stderr="", exit_code=0)

    assert len(findings) == 5
    assert all(f.source_tool == "gobuster" for f in findings)
    assert all(f.kind == "path" for f in findings)
    assert findings[0].value == "/admin (status 301)"
    assert findings[1].value == "/images (status 301)"
    assert findings[2].value == "/index.html (status 200)"
    assert findings[3].value == "/robots.txt (status 200)"
    assert findings[4].value == "/server-status (status 403)"