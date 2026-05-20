import pytest


def test_allowlist():
    from aictfsolver.tools.allowlist import check_target, AllowlistViolation

    allowed_targets = ["target.local", "10.0.0.0/24"]
    # valid cases
    check_target("target.local", allowed_targets)
    check_target("http://target.local:8080/x", allowed_targets)
    check_target("10.0.0.5", allowed_targets) 

    # invalid cases
    with pytest.raises(AllowlistViolation):
        check_target("evil.example.com", allowed_targets)
    with pytest.raises(AllowlistViolation):
        check_target("10.0.1.5", allowed_targets)
    with pytest.raises(AllowlistViolation):
        check_target("target.local.evil.com", allowed_targets)
    with pytest.raises(AllowlistViolation):
        check_target("evil.com#target.local", allowed_targets)
    with pytest.raises(AllowlistViolation):
        check_target("", allowed_targets)
    with pytest.raises(AllowlistViolation):
        check_target("malformed", allowed_targets)

    
def test_allowlist_malformed():
    from aictfsolver.tools.allowlist import check_target, AllowlistViolation

    allowed_targets = ["target.local"]
    with pytest.raises(AllowlistViolation):
        check_target("http://:8080/x", allowed_targets)
    with pytest.raises(AllowlistViolation):
        check_target("http:///x", allowed_targets)
    with pytest.raises(AllowlistViolation):
        check_target("http://", allowed_targets)

def test_allowlist_no_hostname():
    from aictfsolver.tools.allowlist import check_target, AllowlistViolation

    allowed_targets = ["target.local"]
    with pytest.raises(AllowlistViolation):
        check_target("http://:8080/x", allowed_targets)
    with pytest.raises(AllowlistViolation):
        check_target("http:///x", allowed_targets)
    with pytest.raises(AllowlistViolation):
        check_target("http://", allowed_targets)

def test_allowlist_regex_extraction():
    from aictfsolver.tools.allowlist import check_target, AllowlistViolation

    allowed_targets = ["target.local"]
    # regex should extract "target.local" from this malformed input
    check_target("!!!target.local!!!", allowed_targets)
    # but should fail if no valid hostname can be extracted
    with pytest.raises(AllowlistViolation):
        check_target("!!!invalid!!!", allowed_targets)


def test_allowlist_subdomain_trick():
    from aictfsolver.tools.allowlist import check_target, AllowlistViolation

    allowed_targets = ["target.local"]
    # should reject "target.local.evil.com" because hostname is "target.local.evil.com"
    with pytest.raises(AllowlistViolation):
        check_target("target.local.evil.com", allowed_targets)
    # should reject "evil.com#target.local" because hostname is "evil.com"
    with pytest.raises(AllowlistViolation):
        check_target("evil.com#target.local", allowed_targets)

def test_allowlist_empty_and_malformed():
    from aictfsolver.tools.allowlist import check_target, AllowlistViolation

    allowed_targets = ["target.local"]
    with pytest.raises(AllowlistViolation):
        check_target("", allowed_targets)
    with pytest.raises(AllowlistViolation):
        check_target("!!!invalid!!!", allowed_targets)