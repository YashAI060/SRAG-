from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.rag.hybrid_retrieval import HybridRetriever
from app.services.llm_generator import LLMGeneratorService
from app.api.dependencies import RoleChecker
import time

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

class EvalRetrieveRequest(BaseModel):
    query: str
    top_k: int = 5
    retrieval_mode: str = "hybrid"
    decompose: bool = False
    
class EvalRetrieveResponse(BaseModel):
    query: str
    chunks: List[dict]
    trace: Dict[str, Any]

@router.post("/retrieve", response_model=EvalRetrieveResponse)
async def evaluate_retrieve(
    req: EvalRetrieveRequest,
    current_user: dict = Depends(RoleChecker(["admin"])),
):
    """
    Dedicated internal evaluation endpoint.
    Bypasses the confidence gate and LLM generation.
    Returns raw retrieved chunks for evaluation metrics.
    Only accessible by evaluators/admins.
    """
    tenant_id = current_user["tenant_id"]
    llm_svc = LLMGeneratorService()
    retriever = HybridRetriever()
    
    t0 = time.time()
    query_embedding = llm_svc.get_embedding(req.query, task_type="retrieval_query")
    t_embed = time.time() - t0
    
    t1 = time.time()
    chunks, decomp_trace = retriever.retrieve(
        query=req.query,
        query_embedding=query_embedding,
        tenant_id=tenant_id,
        top_k=req.top_k,
        document_ids=None,
        mode=req.retrieval_mode,
        decompose=req.decompose,
    )
    t_retrieve = time.time() - t1
    
    trace = {
        "embedding_ms": t_embed * 1000,
        "retrieval_ms": t_retrieve * 1000,
        "decomposition_status": decomp_trace["status"],
        "decomposition_latency_ms": decomp_trace["latency_ms"],
        "subquery_count": decomp_trace["subquery_count"],
        "subqueries_requested": decomp_trace.get("subqueries_requested", 0),
        "subqueries_accepted": decomp_trace.get("subqueries_accepted", 0),
        "subqueries_truncated": decomp_trace.get("subqueries_truncated", False),
    }
    
    return EvalRetrieveResponse(
        query=req.query,
        chunks=chunks,
        trace=trace
    )
