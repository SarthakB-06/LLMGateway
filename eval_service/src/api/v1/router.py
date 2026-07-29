from fastapi import APIRouter, BackgroundTasks
from src.models.schemas import CompareRequest, JudgeRequest, EvalRunSchema
from src.services.gateway_client import gateway_client
from src.services.judge import evaluate_responses
from src.services.clickhouse_writer import clickhouse_writer
import asyncio
import uuid

router = APIRouter()

@router.post("/compare")
async def compare_models(request: CompareRequest):
    run_id = str(uuid.uuid4())
    
    # Fan out requests concurrently
    tasks = [
        gateway_client.complete(m.provider, m.model, request.prompt) 
        for m in request.models
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    response_data = []
    for model_cfg, res in zip(request.models, results):
        if isinstance(res, Exception):
            response_data.append({"model": model_cfg.model, "error": str(res)})
        else:
            response_data.append({"model": model_cfg.model, **res})
            
    return {"run_id": run_id, "results": response_data}


@router.post("/judge")
async def run_judge(request: JudgeRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    models = list(request.responses.keys())
    
    # Run the judge
    evaluation = await evaluate_responses(request.prompt, request.responses)
    
    # Map results to A and B
    model_a, model_b = models[0], models[1]
    score_a = evaluation.get("response_a", {})
    score_b = evaluation.get("response_b", {})
    
    # Save to ClickHouse in background
    for model, score_data in [(model_a, score_a), (model_b, score_b)]:
        run = EvalRunSchema(
            run_id=run_id,
            prompt=request.prompt,
            model=model,
            response=request.responses[model],
            latency_ms=0, # We'd ideally pass this from /compare output
            cost=0.0,     # We'd ideally pass this from /compare output
            cache_hit=False,
            correctness_score=score_data.get("correctness"),
            completeness_score=score_data.get("completeness"),
            clarity_score=score_data.get("clarity"),
            verdict=evaluation.get("verdict"),
            rationale=score_data.get("rationale")
        )
        background_tasks.add_task(clickhouse_writer.write_run, run)
        
    return {"run_id": run_id, "evaluation": evaluation}
