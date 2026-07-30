from fastapi import APIRouter, BackgroundTasks,Query
from src.models.schemas import CompareRequest, JudgeRequest, EvalRunSchema, RagEvalRequest
from src.services.gateway_client import gateway_client
from src.services.judge import evaluate_responses
from src.services.clickhouse_writer import clickhouse_writer
from src.services.faithfulness import evaluate_rag_response
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


@router.post("/rag-eval")
async def run_rag_eval(request: RagEvalRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())

    scores = evaluate_rag_response(
        question=request.question,
        context=request.context,
        answer=request.answer
    )


    run = EvalRunSchema(
        run_id=run_id,
        prompt=request.question,
        model=request.model,
        response=request.answer,
        latency_ms=0,
        cost=0.0,
        cache_hit=False,
        faithfullness_score=scores["faithfulness_score"],
        groundedness_score=scores["groundedness_score"],
    )

    background_tasks.add_task(clickhouse_writer.write_run, run)

    return {"run_id": run_id, "scores":scores}




@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=100)):
    try:
        query = f"""
        SELECT 
            run_id, timestamp, prompt, model, response, 
            latency_ms, cost, cache_hit, 
            correctness_score, completeness_score, faithfullness_score, groundedness_score, clarity_score, 
            verdict, rationale
        FROM eval_runs
        ORDER BY timestamp DESC
        LIMIT {limit}
        """
        result = clickhouse_writer.client.query(query)
        
        # Format the result nicely for the frontend
        history = []
        for row in result.result_rows:
            history.append({
                "run_id": str(row[0]),
                "timestamp": row[1].isoformat() if row[1] else None,
                "prompt": row[2],
                "model": row[3],
                "response": row[4],
                "latency_ms": row[5],
                "cost": row[6],
                "cache_hit": row[7],
                "correctness_score": row[8],
                "completeness_score": row[9],
                "faithfullness_score":row[10],
                "groundedness_score":row[11],
                "clarity_score": row[12],
                "verdict": row[13],
                "rationale": row[14]
            })
            
        return {"history": history}
    except Exception as e:
        return {"error": str(e)}