from src.core.config import settings
import os 
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.metrics._faithfulness import Faithfulness
from ragas.metrics._answer_relevance import AnswerRelevancy




os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")


def evaluate_rag_response(question: str, context: str, answer: str) -> dict:
    """
    Compute faithfulness and answer relevancy scores using ragas 0.4.3.
    Args:
        question: The user's question.
        context:  The retrieved context passage (single string).
        answer:   The model's answer to evaluate.
    Returns:
        {
            "faithfulness_score":  float | None,
            "groundedness_score":  float | None,
            "error":               str | None,
        }
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_api_key:
        return {
            "faithfulness_score": None,
            "groundedness_score": None,
            "error": "GEMINI_API_KEY not set — cannot run ragas evaluation.",
        }
    try:
        # Wire up Gemini as the ragas LLM + embeddings
        llm = LangchainLLMWrapper(
            ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=gemini_api_key)
        )
        embeddings = LangchainEmbeddingsWrapper(
            GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=gemini_api_key,
            )
        )
        faithfulness_metric = Faithfulness(llm=llm)
        relevancy_metric = AnswerRelevancy(llm=llm, embeddings=embeddings)
        # Build the EvaluationDataset with correct ragas 0.4.x column names
        # retrieved_contexts must be a list of strings
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=[context],  # context is a single string → wrap in list
        )
        dataset = EvaluationDataset(samples=[sample])
        result = evaluate(
            dataset=dataset,
            metrics=[faithfulness_metric, relevancy_metric],
            raise_exceptions=False,
            show_progress=False,
        )
        # result is an EvaluationResult — convert to dict for indexing
        result_dict = result.to_pandas().to_dict(orient="records")[0]
        return {
            "faithfulness_score":  result_dict.get("faithfulness"),
            "groundedness_score":  result_dict.get("answer_relevancy"),
            "error": None,
        }
    except Exception as e:
        return {
            "faithfulness_score": None,
            "groundedness_score": None,
            "error": str(e),
        }