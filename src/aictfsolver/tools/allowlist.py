import ipaddress

class AllowlistViolation(Exception):
    """Raised when an action violates the allowlist."""

    pass

def check_target(candidate, allowed_targets):
    """
    Check if the candidate target is in the allowed targets list.
    This function should be robust against common tricks like subdomain attacks,
    URL encoding, and malformed inputs.

    Args:
        candidate (str): The target to check.
        allowed_targets (List[str]): The list of allowed targets.

    Raises:
        AllowlistViolation: If the candidate is not allowed.
    """

    # Basic check: candidate must be in allowed_targets
    if candidate in allowed_targets:
        return

    import re
    hostname_pattern = re.compile(r'([a-zA-Z0-9.-]+)')
    # remove https://, www., and any path/query fragments to extract the hostname
    candidate = candidate.replace("https://", "").replace("http://", "").replace("www.", "")
    match = hostname_pattern.search(candidate)
    if match:
        hostname = match.group(1) 
        if hostname in allowed_targets:
            return
    

    if candidate.endswith('.'):
        stripped_candidate = candidate.rstrip('.')
        if stripped_candidate in allowed_targets:
            return
        

    try:
        candidate_ip = ipaddress.ip_address(candidate)
        for allowed in allowed_targets:
            try:
                if '/' in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if candidate_ip in network:
                        return
                else:
                    if candidate_ip == ipaddress.ip_address(allowed):
                        return
            except ValueError:
                continue  # not an IP or CIDR, ignore
    except ValueError:
        pass  # not an IP address, ignore

    raise AllowlistViolation(f"Target '{candidate}' is not in the allowlist.")
    
