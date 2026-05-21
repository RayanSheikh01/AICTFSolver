import pytest

from aictfsolver.tools.parsers.curl_headers import parse_curl_headers_output

def test_curl_parser():
    # read curl headers fixture
    with open("tests/fixtures/curl_headers_basic.txt") as f:
        curl_output = f.read()
    findings = parse_curl_headers_output(curl_output, stderr="", exit_code=0)
    
    assert len(findings) == 9
    assert all(f.source_tool == "curl_headers" for f in findings)
    assert findings[0].kind == "status"
    assert findings[0].value == "200"
    assert findings[1].kind == "header_date"
    assert findings[1].value == "Tue, 21 May 2026 12:34:56 GMT"
    assert findings[2].kind == "header_server"
    assert findings[2].value == "nginx/1.25.3"
    assert findings[3].kind == "header_content-type"
    assert findings[3].value == "text/html; charset=UTF-8"
    assert findings[4].kind == "header_content-length"
    assert findings[4].value == "1270"
    assert findings[5].kind == "header_connection"
    assert findings[5].value == "keep-alive"
    assert findings[6].kind == "header_x-powered-by"
    assert findings[6].value == "PHP/8.2.10"
    assert findings[7].kind == "header_set-cookie"
    assert findings[7].value == "PHPSESSID=abc123def456; path=/; HttpOnly"
    assert findings[8].kind == "header_cache-control"
    assert findings[8].value == "no-store, no-cache, must-revalidate"
    
    
    