import pytest

from aictfsolver.tools.parsers.whatweb import parse_whatweb_output

def test_whatweb_parser():
    # read what web fixture
    with open("tests/fixtures/whatweb_basic.txt") as f:
        whatweb_output = f.read()
    findings = parse_whatweb_output(whatweb_output, stderr="", exit_code=0)
    assert len(findings) == 4
    assert all(f.source_tool == "whatweb" for f in findings)
    assert findings[0].kind == "server"
    assert findings[0].value == "nginx/1.18.0"
    assert findings[1].kind == "ip"
    assert findings[1].value == "93.184.216.34"
    assert findings[2].kind == "title"
    
    assert findings[2].value == "Example Domain"
    assert findings[3].kind == "powered_by"
    assert findings[3].value == "PHP/7.4.3"
    
    