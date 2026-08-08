# schemas.py — v2 (eval service upgrade: bias-mitigated judge, CI, feedback loop)
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
    responses: Dict[str, str]
    task_type: Optional[str] = "general" 

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

    judge_verdict: Optional[str] = None    

    task_type: Optional[str] = None         
    prompt_version: Optional[str] = None    

    faithfullness_score: Optional[int] = None   
    groundedness_score: Optional[int] = None    

    faithfulness_score: Optional[float] = None  
    rag_groundedness_score: Optional[float] = None 


class RagEvalRequest(BaseModel):
    question: str
    context: str
    answer: str
    model: str


class RecommendRequest(BaseModel):
    task_type: str = "general"
    min_quality_threshold: float = 3.5  # 1-5 scale


class RecommendResponse(BaseModel):
    recommended_model: Optional[str] = None
    expected_cost: Optional[float] = None
    expected_quality_lower_bound: Optional[float] = None
    confidence_interval: Optional[dict] = None
    error: Optional[str] = None
    fallback: Optional[str] = None

