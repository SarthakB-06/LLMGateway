from fastapi import APIRouter, BackgroundTasks,Query
from src.models.schemas import CompareRequest, JudgeRequest, EvalRunSchema, RagEvalRequest, RecommendRequest, RecommendResponse
from src.services.gateway_client import gateway_client
from src.services.judge import evaluate_responses
from src.services.clickhouse_writer import clickhouse_writer
from src.services.faithfulness import evaluate_rag_response
from src.services.stats import bootstrap_ci, composite_score
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
    judge_verdict = evaluation.get("judge_verdict")

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
            judge_verdict=judge_verdict,
            rationale=score_data.get("rationale"),
            task_type=request.task_type
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
        faithfulness_score=scores.get("faithfulness_score"),
        rag_groundedness_score=scores.get("groundedness_score"),
        faithfullness_score=None,
        groundedness_score=None,
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
            correctness_score, completeness_score, faithfullness_score,
            groundedness_score, clarity_score,
            verdict, judge_verdict, rationale,
            task_type, prompt_version,
            faithfulness_score, rag_groundedness_score
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
                "judge_verdict": row[14],    
                "rationale": row[15],
                "task_type": row[16],
                "prompt_version": row[17],
                "faithfulness_score":row[18],
                "rag_groundedness_score":row[19],
            })
        
        model_scores : dict = {}
        for h in history:
            cs = composite_score(h["correctness_score"], h["completeness_score"], h["clarity_score"])
            if cs is not None:
                model_scores.setdefault(h["model"], []).append(cs)

        model_summary = {}
        for model, scores in model_scores.items():
            model_summary[model] = bootstrap_ci(scores)
        
        return {"history": history, "model_summary": model_summary}
    except Exception as e:
        return {"error": str(e)}



@router.post("/recommend", response_model=RecommendResponse)
async def recommend_model(request: RecommendRequest):
    """
    Query eval_runs for recent scores grouped by model (for this task_type),
    apply bootstrap CI, and return the cheapest model whose CI lower bound
    meets min_quality_threshold.
    """
    try:

        query = f"""
        SELECT
            model,
            correctness_score,
            completeness_score,
            clarity_score,
            cost
        FROM eval_runs
        WHERE task_type = '{request.task_type}'
          AND correctness_score IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 200
        """
        result = clickhouse_writer.client.query(query)
        if not result.result_rows:
            return RecommendResponse(
                error="insufficient_data",
                fallback="gemini-2.5-flash",
            )
        # Group by model
        model_data: dict = {}  # model → {scores: [], costs: []}
        for row in result.result_rows:
            model, corr, comp, clar, cost = row[0], row[1], row[2], row[3], row[4]
            cs = composite_score(corr, comp, clar)
            if cs is not None:
                model_data.setdefault(model, {"scores": [], "costs": []})
                model_data[model]["scores"].append(cs)
                model_data[model]["costs"].append(float(cost))


        # Compute CI and filter by threshold

        qualifying = []
        for model, data in model_data.items():
            if len(data["scores"]) < 3:
                continue  # not enough data for meaningful CI
            ci = bootstrap_ci(data["scores"])
            avg_cost = sum(data["costs"]) / len(data["costs"])
            if ci["lower"] >= request.min_quality_threshold:
                qualifying.append({
                    "model": model,
                    "ci": ci,
                    "avg_cost": avg_cost,
                })
        if not qualifying:
            return RecommendResponse(
                error="no_model_meets_threshold",
                fallback="gemini-2.5-flash",
            )
        # Pick the cheapest qualifying model
        best = min(qualifying, key=lambda x: x["avg_cost"])
        return RecommendResponse(
            recommended_model=best["model"],
            expected_cost=round(best["avg_cost"], 8),
            expected_quality_lower_bound=best["ci"]["lower"],
            confidence_interval=best["ci"],
        )
    except Exception as e:
        return RecommendResponse(
            error=str(e),
            fallback="gemini-2.5-flash",
        )


@router.get("/pareto")
async def get_pareto():
    """
    Returns avg judge score (with bootstrap CI) vs avg cost per model,
    with is_pareto_optimal flag. A model is Pareto-dominated if another model
    has a strictly higher quality lower-bound AND strictly lower avg cost.
    """
    try:
        query = """
        SELECT
            model,
            correctness_score,
            completeness_score,
            clarity_score,
            cost
        FROM eval_runs
        WHERE correctness_score IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 500
        """
        result = clickhouse_writer.client.query(query)
        model_data: dict = {}
        for row in result.result_rows:
            model, corr, comp, clar, cost = row[0], row[1], row[2], row[3], row[4]
            cs = composite_score(corr, comp, clar)
            if cs is not None:
                model_data.setdefault(model, {"scores": [], "costs": []})
                model_data[model]["scores"].append(cs)
                model_data[model]["costs"].append(float(cost))
        models_out = []
        for model, data in model_data.items():
            if not data["scores"]:
                continue
            ci = bootstrap_ci(data["scores"])
            avg_cost = sum(data["costs"]) / len(data["costs"])
            models_out.append({
                "model":     model,
                "avg_quality": ci["mean"],
                "avg_cost":  round(avg_cost, 8),
                "quality_ci": ci,
                "run_count": ci["n"],
                "is_pareto_optimal": True,  # set below
            })
        # Mark dominated models
        for m in models_out:
            for other in models_out:
                if other["model"] == m["model"]:
                    continue
                # m is dominated if other has higher lower-bound quality AND lower cost
                if (
                    other["quality_ci"]["lower"] > m["quality_ci"]["lower"]
                    and other["avg_cost"] < m["avg_cost"]
                ):
                    m["is_pareto_optimal"] = False
                    break
        return {"models": models_out}
    except Exception as e:
        return {"error": str(e)}




    