from pydantic import BaseModel
from typing import List, Dict, Optional

class ModelConfig(BaseModel):
    provider: str
    model: str

class CompareRequest(BaseModel):
    prompt: str
    models: List[ModelConfig]

class JudgeRequest(BaseModel):
    prompt: str
    responses: Dict[str, str] # e.g. {"model_a": "response...", "model_b": "..."}

class EvalRunSchema(BaseModel):
    run_id: str
    prompt: str
    model: str
    response: str
    latency_ms: int
    cost: float
    cache_hit: bool
    correctness_score: Optional[int] = None
    completeness_score: Optional[int] = None
    clarity_score: Optional[int] = None
    verdict: Optional[str] = None
    rationale: Optional[str] = None
