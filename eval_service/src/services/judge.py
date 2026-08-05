import json
from src.services.gateway_client import gateway_client
from src.core.config import settings

RUBRIC_TEMPLATE = """
You are an impartial evaluator comparing responses to the same prompt.
Prompt: {prompt}
Response A ({model_a}): {response_a}
Response B ({model_b}): {response_b}
Score EACH response from 1-5 on:
1. Correctness — factually accurate, directly answers the prompt
2. Completeness — covers what was asked without major omissions
3. Clarity — well-organized, unambiguous, appropriately concise
Return strict JSON only (no markdown formatting, just raw JSON). Format:
{{
  "response_a": {{"correctness": <int>, "completeness": <int>, "clarity": <int>, "rationale": "<str>"}},
  "response_b": {{"correctness": <int>, "completeness": <int>, "clarity": <int>, "rationale": "<str>"}},
  "verdict": "A" | "B" | "tie"
}}
"""

def _flip_verdict(verdict: str) -> str:
    """Normalise a verdict from a swapped-order call back to original A/B labels."""
    if verdict == "A":
        return "B"
    if verdict == "B":
        return "A"
    return verdict 

async def _call_judge(prompt: str, model_a: str, response_a: str, model_b: str, response_b: str) -> dict:
    """Single judge call. Returns parsed JSON dict."""
    eval_prompt = RUBRIC_TEMPLATE.format(
        prompt=prompt,
        model_a=model_a,
        response_a=response_a,
        model_b=model_b,
        response_b=response_b,
    )
    res = await gateway_client.complete(
        provider=settings.JUDGE_PROVIDER,
        model=settings.JUDGE_MODEL,
        prompt=eval_prompt,
        json_mode=True,
    )
    raw_json = res["response"].strip()
    if raw_json.startswith("```json"):
        raw_json = raw_json[7:]
    if raw_json.endswith("```"):
        raw_json = raw_json[:-3]
    raw_json = raw_json.strip()
    parsed = json.loads(raw_json)
    parsed["_metrics"] = {
        "latency_ms": res["latency_ms"],
        "cost": res["cost"],
    }
    return parsed

async def evaluate_responses(prompt: str, responses: dict):
    """
    Bias-mitigated judge: runs two calls with A/B order swapped.
    
    - If both agree on winner → confident verdict stored in `judge_verdict`
    - If they disagree      → `judge_verdict = "inconclusive"`
    
    The first call's scores for response_a / response_b are always returned
    in canonical order (keyed by the original model names). `judge_verdict`
    is the bias-corrected field; `verdict` preserves the raw first-pass verdict
    for traceability.
    """
    models = list(responses.keys())
    if len(models) != 2:
        raise ValueError("Judge currently supports exactly 2 responses for comparison.")
        
    model_a, model_b = models[0], models[1]
    resp_a, resp_b = responses[model_a], responses[model_b]

    run1 = await _call_judge(prompt, model_a, resp_a, model_b, resp_b)
    verdict1 = run1.get("verdict", "tie")


    run2 = await _call_judge(prompt, model_b, resp_b, model_a, resp_a)
    raw_verdict2 = run2.get("verdict", "tie")

    verdict2_normalised = _flip_verdict(raw_verdict2)

    if verdict1 == verdict2_normalised:
        judge_verdict = verdict1
    else:
        judge_verdict = "inconclusive"
    

    total_latency = run1["_metrics"]["latency_ms"] + run2["_metrics"]["latency_ms"]
    total_cost = run1["_metrics"]["cost"] + run2["_metrics"]["cost"]



    
    return {
        "response_a": run1.get("response_a", {}),
        "response_b": run1.get("response_b", {}),
        "verdict": verdict1,              
        "judge_verdict": judge_verdict,   
        "run2_verdict_raw": raw_verdict2, 
        "_judge_metrics": {
            "latency_ms": total_latency,
            "cost": total_cost,
            "run1_verdict": verdict1,
            "run2_verdict_normalised": verdict2_normalised,
        },
    }