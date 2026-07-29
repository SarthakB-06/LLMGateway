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

async def evaluate_responses(prompt: str, responses: dict):
    # Only supports comparing 2 models currently as per rubric shape
    models = list(responses.keys())
    if len(models) != 2:
        raise ValueError("Judge currently supports exactly 2 responses for comparison.")
        
    model_a, model_b = models[0], models[1]
    
    eval_prompt = RUBRIC_TEMPLATE.format(
        prompt=prompt,
        model_a=model_a,
        response_a=responses[model_a],
        model_b=model_b,
        response_b=responses[model_b]
    )
    
    # Call the judge via the gateway internal endpoint!
    res = await gateway_client.complete(
        provider=settings.JUDGE_PROVIDER,
        model=settings.JUDGE_MODEL,
        prompt=eval_prompt,
        json_mode=True
    )
    
    # Strip markdown if present
    raw_json = res["response"].strip()
    if raw_json.startswith("```json"):
        raw_json = raw_json[7:-3]
        
    try:
        parsed_result = json.loads(raw_json)
        # Add latency/cost of the judge call to the payload for reference if needed
        parsed_result["_judge_metrics"] = {
            "latency_ms": res["latency_ms"],
            "cost": res["cost"]
        }
        return parsed_result
    except json.JSONDecodeError:
        raise Exception(f"Failed to parse judge response: {res['response']}")
