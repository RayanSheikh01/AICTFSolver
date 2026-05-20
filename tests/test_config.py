import pytest
import json

from aictfsolver.config import load_challenge

def test_load_challenge(tmp_path):
    challenge_data = {
        "description": "A sample challenge",
        "target": "example.com",
        "flag_format": "flag{.*}",
        "allowed_targets": ["example.com", "test.com"],
        "category_hint": "web",
        "dangerous_tools_allowed": ["nmap"],
        "budget": {
            "iterations_used": 0,
            "iterations_max": 100,
            "tool_calls_used": 0,
            "tool_calls_max": 50,
            "wall_clock_s_used": 0.0,
            "wall_clock_s_max": 3600.0
        }
    }
    challenge_path = tmp_path / "challenge.json"
    with open(challenge_path, 'w') as f:
        json.dump(challenge_data, f)
    
    spec = load_challenge(challenge_path)
    assert spec.description == challenge_data["description"]
    assert spec.target == challenge_data["target"]
    assert spec.flag_format == challenge_data["flag_format"]
    assert spec.allowed_targets == challenge_data["allowed_targets"]
    assert spec.category_hint == challenge_data["category_hint"]
    assert spec.dangerous_tools_allowed == challenge_data["dangerous_tools_allowed"]
    assert spec.budget.iterations_used == challenge_data["budget"]["iterations_used"]
    assert spec.budget.iterations_max == challenge_data["budget"]["iterations_max"]
    assert spec.budget.tool_calls_used == challenge_data["budget"]["tool_calls_used"]
    assert spec.budget.tool_calls_max == challenge_data["budget"]["tool_calls_max"]
    assert spec.budget.wall_clock_s_used == challenge_data["budget"]["wall_clock_s_used"]
    assert spec.budget.wall_clock_s_max == challenge_data["budget"]["wall_clock_s_max"]

