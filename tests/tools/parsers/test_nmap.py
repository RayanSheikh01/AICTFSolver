from aictfsolver.tools.parsers.nmap import parse_nmap_output


def test_nmap_parser():
    with open("tests/fixtures/nmap_basic.txt") as f:
        nmap_output = f.read()

    findings = parse_nmap_output(nmap_output, stderr="", exit_code=0)

    assert len(findings) == 3
    assert all(f.source_tool == "nmap" for f in findings)
    assert all(f.kind == "open_port" for f in findings)
    assert findings[0].value == "22/tcp ssh OpenSSH 7.4 (protocol 2.0)"
    assert findings[1].value == "80/tcp http Apache httpd 2.4.6 ((CentOS))"
    assert findings[2].value == "443/tcp https Apache httpd 2.4.6 ((CentOS))"
