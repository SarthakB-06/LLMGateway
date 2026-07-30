from ragas import evaluate
from ragas.metrics import _faithfulness, _answer_relevancy
from datasets import Dataset
from src.core.config import settings
import os 



os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")


def evaluate_rag_response(question:str, context:str, answer:str) -> dict:
    data = {
        "question": [question],
        "context": [[context]],
        "answer" : [answer],
    }

    dataset = Dataset.from_dict(data)

    result = evaluate(dataset, metrics=[_faithfulness, _answer_relevancy])



    return {
        "faithfulness_score": result["faithfulness"][0],
        "groundedness_score": result["answer_relevancy"][0]
    }