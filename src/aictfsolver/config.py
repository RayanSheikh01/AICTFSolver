import json
from pathlib import Path


from aictfsolver.state import ChallengeSpec


from aictfsolver.state import ChallengeSpec


def load_challenge(path: Path) -> ChallengeSpec:
    with open(path, 'r') as f:
        data = json.load(f)
    return ChallengeSpec(**data)

