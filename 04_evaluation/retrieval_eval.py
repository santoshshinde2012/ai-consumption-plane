# Databricks notebook source
# MAGIC %pip install "mlflow>=3.1" databricks-ai-search databricks-sdk --quiet
# MAGIC %restart_python

# COMMAND ----------
"""Evaluation · retrieval quality as a contract.

Two loops, per the article's Step 10:
  A) TUNING  — hit-rate@k for HYBRID vs pure-ANN against a ground-truth set
     (one knob at a time; let the metrics decide). Logged to MLflow runs.
  B) JUDGING — MLflow 3 RetrievalGroundedness over a traced retriever span,
     with real Foundation-Model-API generation grounded on retrieved context.
Docs: https://docs.databricks.com/aws/en/mlflow3/genai/
"""
import json
import pathlib

import mlflow
from databricks.sdk import WorkspaceClient
from mlflow.entities import Document
from mlflow.genai.scorers import RetrievalGroundedness

import config
from lib.ai_search import get_search_client

index = get_search_client().get_index(
    endpoint_name=config.VS_ENDPOINT, index_name=config.VS_INDEX
)

EVAL = [
    json.loads(line)
    for line in pathlib.Path(__file__).with_name("eval_dataset.jsonl").read_text().splitlines()
    if line.strip()
]

COLS = config.INDEX_QUERY_COLUMNS  # chunk_id, chunk_content, source_uri, chunk_position


def search(query: str, query_type: str, k: int = config.EVAL_TOP_K):
    hits = index.similarity_search(
        query_text=query,
        columns=COLS,
        num_results=k,
        query_type=query_type,
    )
    return [dict(zip(COLS, row)) for row in hits.get("result", {}).get("data_array", [])]


# --- A) Tuning: hit-rate@k, HYBRID vs ANN --------------------------------------
mlflow.set_experiment("/Shared/ai-consumption-plane-retrieval")
for query_type in ["HYBRID", "ANN"]:
    with mlflow.start_run(run_name=f"hit_rate_{query_type}"):
        hits_at_k = 0
        for ex in EVAL:
            rows = search(ex["query"], query_type)
            if any(ex["expected_source"] in str(r["source_uri"]) for r in rows):
                hits_at_k += 1
        rate = hits_at_k / len(EVAL)
        mlflow.log_param("query_type", query_type)
        mlflow.log_param("k", config.EVAL_TOP_K)
        mlflow.log_metric("hit_rate_at_k", rate)
        print(f"{query_type}: hit-rate@{config.EVAL_TOP_K} = {rate:.2f}")


# --- B) Judging: RetrievalGroundedness over a traced retriever + real LLM -------
@mlflow.trace(span_type="RETRIEVER")  # enables retrieval-specific judges
def retrieve(query: str):
    return [
        Document(
            id=r["chunk_id"],
            page_content=r["chunk_content"],
            metadata={"source": r["source_uri"], "position": r["chunk_position"]},
        )
        for r in search(query, "HYBRID")
    ]


def rag_answer(query: str) -> str:
    """Grounded generation: answer only from retrieved context, cite sources."""
    docs = retrieve(query)
    if not docs:
        return "No supporting document found."
    context = "\n\n".join(f"[{d.metadata['source']}] {d.page_content}" for d in docs)
    llm = WorkspaceClient().serving_endpoints.get_open_ai_client()
    resp = llm.chat.completions.create(
        model=config.LLM_ENDPOINT,  # any Foundation Model API chat endpoint
        messages=[
            {"role": "system", "content": "Answer only from the provided context. Cite sources."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
    )
    return resp.choices[0].message.content


mlflow.genai.evaluate(
    data=[{"inputs": {"query": ex["query"]}} for ex in EVAL],
    predict_fn=rag_answer,  # inputs keys map to predict_fn kwargs
    scorers=[RetrievalGroundedness()],
)
print("Groundedness evaluation complete — open the MLflow experiment UI for per-question scores.")
