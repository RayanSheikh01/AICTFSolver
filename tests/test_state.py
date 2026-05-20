import pytest

from aictfsolver.state import BudgetCounters, ChallengeSpec, new_state

def test_agent_state_initialization():
    counters = BudgetCounters(
        iterations_used=0,
        iterations_max=100,
        tool_calls_used=0,
        tool_calls_max=50,
        wall_clock_s_used=0.0,
        wall_clock_s_max=3600.0
    )
    spec = ChallengeSpec(
        description="A sample challenge",
        target="example.com",
        flag_format="flag{.*}",
        allowed_targets=["example.com", "test.com"],
        category_hint="web",
        dangerous_tools_allowed=["nmap"],
        budget=counters
    )
    state = new_state(spec=spec)
    assert state["phase"] == "triage"
    assert state["findings"] == []
    assert state["hypotheses"] == []
    assert state["attempts"] == []
    assert state["logs"] == []
    assert state["human_messages"] == []
    assert state["candidate_flags"] == []

def test_agent_state_invalid_allowed_targets():
    with pytest.raises(ValueError):
        ChallengeSpec(
            description="A sample challenge",
            target="example.com",
            flag_format="flag{.*}",
            allowed_targets=[],
            category_hint="web",
            dangerous_tools_allowed=["nmap"],
            budget=BudgetCounters(
                iterations_used=0,
                iterations_max=100,
                tool_calls_used=0,
                tool_calls_max=50,
                wall_clock_s_used=0.0,
                wall_clock_s_max=3600.0
            )
        )


## example usage

if __name__ == "__main__":
    pytest.main([__file__])
    




