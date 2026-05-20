from typing import List, TypedDict
from pydantic import BaseModel, Field, validator

class BudgetCounters(BaseModel):
    iterations_used: int = 0
    iterations_max: int
    tool_calls_used: int = 0
    tool_calls_max: int
    wall_clock_s_used: float = 0.0
    wall_clock_s_max: float

    def exceeded(self) -> bool:
        return (self.iterations_used >= self.iterations_max or
                self.tool_calls_used >= self.tool_calls_max or
                self.wall_clock_s_used >= self.wall_clock_s_max)
    
class ChallengeSpec(BaseModel):
    description: str
    target: str
    flag_format: str
    allowed_targets: List[str]
    category_hint: str
    dangerous_tools_allowed: List[str]
    budget: BudgetCounters

    @validator('allowed_targets')
    def non_empty_allowed_targets(cls, v):
        if not v:
            raise ValueError('allowed_targets must be a non-empty list')
        return v
    
class Finding(BaseModel):
    source_tool: str
    kind: str
    value: str
    confidence: float

class Hypothesis(BaseModel):
    id: int
    text: str
    rank: int
    status: str
    basis: str

class Attempt(BaseModel):
    hypothesis_id: int
    tool: str
    args: List[str]
    exit_code: int
    summary: str
    raw_log_path: str

class LogEntry(BaseModel):
    node: str
    ts: float
    kind: str
    content: str

class HumanTurn(BaseModel):
    kind: str
    payload: str

class AgentState(TypedDict):
    phase: str
    spec: ChallengeSpec
    findings: List[Finding]
    hypotheses: List[Hypothesis]
    attempts: List[Attempt]
    logs: List[LogEntry]
    human_messages: List[HumanTurn]
    candidate_flags: List[str]
    


def new_state(spec: ChallengeSpec) -> AgentState:
    return AgentState(
        phase="triage",
        spec=spec,
        findings=[],
        hypotheses=[],
        attempts=[],
        logs=[],
        human_messages=[],
        candidate_flags=[]
    )