"""
RAG Evaluation & Benchmarking script.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import statistics

import requests

from evaluation.metrics import (
    citation_precision,
    citation_recall,
    evaluate_answer_relevancy,
    evaluate_faithfulness,
    mrr,
    precision_at_k,
    recall_at_k,
    ndcg_at_k
)

DATASETS_DIR = Path(__file__).parent / "datasets_v2"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def _ask(api_url: str, token: str, question: str, mode: str = "full") -> dict:
    resp = requests.post(
        f"{api_url}/api/v1/chat/ask",
        headers=_headers(token),
        json={
            "query": question,
            "retrieval_mode": mode,
            "top_k": 5,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()

def run_preflight(api_url: str, token: str) -> dict:
    with open(DATASETS_DIR / "manifest.json") as f:
        manifest = json.load(f)
        
    with open(DATASETS_DIR / "qa_dataset.json") as f:
        qa_data = json.load(f)
        
    resp = requests.get(f"{api_url}/api/v1/docs/", headers=_headers(token))
    resp.raise_for_status()
    docs = resp.json().get("documents", [])
    
    active_docs = [d for d in docs if d.get("is_active", True) and d.get("status") == "ready"]
    failed_docs = [d for d in docs if d.get("status") == "failed"]
    total_chunks = sum(d.get("chunk_count", 0) for d in active_docs)
    
    answerable = [q for q in qa_data if q.get("is_answerable", True)]
    unanswerable = [q for q in qa_data if not q.get("is_answerable", True)]
    
    print("\n============================================================")
    print("SECURE RAG BENCHMARK")
    print("============================================================")
    print(f"Dataset Version:       {manifest.get('dataset_version', '1.0')}")
    print(f"Corpus Version:        {manifest.get('corpus_version', '1.0')}")
    print(f"Tenant:                benchmark\n")
    print("Documents")
    print("------------------------------------------------------------")
    print(f"Documents:             {len(docs)}")
    print(f"Active Documents:      {len(active_docs)}")
    print(f"Indexed Chunks:        {total_chunks}")
    print(f"Failed Documents:      {len(failed_docs)}\n")
    print("Questions")
    print("------------------------------------------------------------")
    print(f"Total:                 {len(qa_data)}")
    print(f"Answerable:            {len(answerable)}")
    print(f"Unanswerable:          {len(unanswerable)}\n")
    
    if len(active_docs) == 0:
        print("Status:                ❌ PREFLIGHT FAILED (Corpus Empty)")
        print("============================================================")
        sys.exit(1)
        
    print("Status:                ✓ PREFLIGHT PASSED")
    print("============================================================")
    
    return {
        "active_docs": active_docs,
        "qa_data": qa_data,
        "answerable": answerable,
        "unanswerable": unanswerable,
        "manifest": manifest
    }

def run_retrieval_ablation(api_url: str, token: str, qa_data: list, active_docs: list):
    import math as _math

    MODES = ["dense", "bm25", "hybrid", "hybrid_decomp", "hybrid_rerank"]
    MODE_LABELS = {
        "dense": "Dense",
        "bm25": "BM25",
        "hybrid": "Hybrid RRF (Orig)",
        "hybrid_decomp": "Hybrid + Decomp",
        "hybrid_rerank": "Hybrid + Rerank",
    }

    print("\nRETRIEVAL ABLATION")
    print("============================================================")

    answerable   = [q for q in qa_data if q.get("is_answerable", True)]
    unanswerable = [q for q in qa_data if not q.get("is_answerable", True)]
    doc_name_to_id = {d["filename"]: d["document_id"] for d in active_docs}

    results_by_mode: dict = {m: [] for m in MODES}
    # Track per-query reranker status counts
    reranker_active = reranker_fallback = reranker_error = 0
    decomp_active = decomp_fallback = decomp_error = 0

    print(f"Running {len(answerable)} answerable queries x {len(MODES)} modes ...")

    for item in answerable:
        qid     = item["id"]
        q       = item["question"]
        src_doc = item.get("source_document")
        rel_doc_id = doc_name_to_id.get(src_doc)
        gt_pages   = item.get("ground_truth_pages", [])
        q_type     = item.get("type", "other")

        if not rel_doc_id:
            continue

        per_mode_retrieved: dict = {}

        for mode in MODES:
            t0 = time.perf_counter()
            actual_mode = "hybrid" if mode == "hybrid_decomp" else mode
            decompose = (mode == "hybrid_decomp")
            try:
                resp = requests.post(
                    f"{api_url}/api/v1/evaluation/retrieve",
                    json={"query": q, "retrieval_mode": actual_mode, "top_k": 5, "decompose": decompose},
                    headers=_headers(token),
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                chunks = data.get("chunks", [])
                trace = data.get("trace", {})
                
                if decompose:
                    d_status = trace.get("decomposition_status", "INACTIVE")
                    if d_status == "ACTIVE":
                        decomp_active += 1
                    elif d_status == "FALLBACK":
                        decomp_fallback += 1
                    elif d_status == "ERROR":
                        decomp_error += 1

                retrieved = []
                for c in chunks:
                    c_doc  = c.get("document_id", "")
                    c_page = c.get("page_number", 0)
                    is_match = (c_doc == rel_doc_id) and (not gt_pages or c_page in gt_pages)
                    retrieved.append({
                        "doc": c_doc, "page": c_page,
                        "is_match": is_match, "score": c.get("score", 0),
                    })

                per_mode_retrieved[mode] = retrieved

                # ---- NEW METRICS ----
                # Which required gt_pages were found in the top-5?
                pages_found_in_top5 = set()
                for r in retrieved[:5]:
                    if r["doc"] == rel_doc_id and r["page"] in gt_pages:
                        pages_found_in_top5.add(r["page"])

                n_gt = len(gt_pages) if gt_pages else 1
                chunk_recall = len(pages_found_in_top5) / n_gt
                mh_success   = 1.0 if len(pages_found_in_top5) == n_gt else 0.0

                # MRR: rank of first matching chunk (any gt page)
                hit_ranks = [i for i, r in enumerate(retrieved) if r["is_match"]]
                m_score   = 1.0 / (hit_ranks[0] + 1) if hit_ranks else 0.0

                # NDCG@5
                dcg  = sum(1.0 / _math.log2(i + 2) for i in hit_ranks if i < 5)
                idcg = sum(1.0 / _math.log2(i + 2) for i in range(min(5, n_gt)))
                ndcg5 = dcg / idcg if idcg > 0 else 0.0

                latency = (time.perf_counter() - t0) * 1000
                results_by_mode[mode].append({
                    "qid": qid, "q": q, "gt_doc": src_doc,
                    "gt_pages": gt_pages, "type": q_type,
                    "chunk_recall": chunk_recall,
                    "mh_success":   mh_success,
                    "mrr": m_score, "ndcg5": ndcg5,
                    "lat": latency,
                    "retrieved": retrieved,
                })

            except Exception as e:
                print(f"  Error on {qid}/{mode}: {e}")

        # Detect reranker status (compare hybrid vs hybrid_rerank output)
        hy = per_mode_retrieved.get("hybrid", [])
        hr = per_mode_retrieved.get("hybrid_rerank", [])
        if hy and hr:
            if hy == hr:
                reranker_fallback += 1
            else:
                reranker_active += 1
        elif not hr:
            reranker_error += 1

    # ---- Unanswerable retrieval probe -------------------------------------
    # For unanswerable questions: does the retriever confidently return chunks?
    # High top-1 score on an unanswerable query is a false-positive risk.
    SCORE_THRESHOLD = 0.50   # heuristic; dense cosine similarity
    unans_fp_risk = 0

    print(f"\nProbing {len(unanswerable)} unanswerable queries (dense only) ...")
    for item in unanswerable:
        try:
            resp = requests.post(
                f"{api_url}/api/v1/evaluation/retrieve",
                json={"query": item["question"], "retrieval_mode": "dense", "top_k": 1},
                headers=_headers(token),
                timeout=20,
            )
            resp.raise_for_status()
            chunks = resp.json().get("chunks", [])
            if chunks and chunks[0].get("score", 0) >= SCORE_THRESHOLD:
                unans_fp_risk += 1
        except Exception:
            pass

    # ---- Failure classification -------------------------------------------
    # Classify failures for dense+bm25 pairs only (hybrid_rerank fallback adds noise)
    failure_counts = {"SEM_MISS": 0, "LEX_MISS": 0, "BOTH_MISS": 0, "RRF_DEMOTE": 0}

    dense_results  = results_by_mode["dense"]
    bm25_results   = results_by_mode["bm25"]
    rrf_results    = results_by_mode["hybrid"]

    for i in range(min(len(dense_results), len(bm25_results), len(rrf_results))):
        d_res = dense_results[i]
        b_res = bm25_results[i]
        r_res = rrf_results[i]

        gt_pages = d_res["gt_pages"]
        doc_id   = doc_name_to_id.get(d_res["gt_doc"])

        def found(result):
            return any(
                r["doc"] == doc_id and r["page"] in gt_pages
                for r in result["retrieved"][:5]
            )

        d_hit = found(d_res)
        b_hit = found(b_res)
        r_hit = found(r_res)

        if r_hit:
            continue  # Not a failure

        if d_hit and not b_hit:
            failure_counts["LEX_MISS"] += 1    # Dense found it, BM25 missed
        elif b_hit and not d_hit:
            failure_counts["SEM_MISS"] += 1    # BM25 found it, Dense missed
        elif d_hit or b_hit:
            failure_counts["RRF_DEMOTE"] += 1  # At least one found it, RRF demoted below rank 5
        else:
            failure_counts["BOTH_MISS"] += 1   # Neither retriever found it

    # ---- Per-query diagnostics (sample of 8) ------------------------------
    print("\nPER-QUERY DIAGNOSTICS (sample)")
    print("============================================================")
    printed = 0
    for i in range(len(dense_results)):
        if printed >= 8:
            break
        try:
            r_dense  = dense_results[i]
            r_bm25   = bm25_results[i]
            r_hybrid = rrf_results[i]
            r_rerank = results_by_mode["hybrid_rerank"][i]
        except IndexError:
            continue

        print(f"\nQ[{r_dense['type']}]: {r_dense['q']}")
        print(f"GT: {r_dense['gt_doc']}  pages={r_dense['gt_pages']}")

        for label, res in [("Dense", r_dense), ("BM25", r_bm25), ("RRF", r_hybrid)]:
            cr = f"CR={res['chunk_recall']:.1f}"
            print(f"\n  {label} ({cr}):")
            for rank, c in enumerate(res["retrieved"]):
                mark = "+" if c["is_match"] else "-"
                print(f"    #{rank+1} {c['doc'][:8]}.. p{c['page']}  [{mark}]  {c['score']:.4f}")

        print(f"\n  Reranker:")
        if r_hybrid["retrieved"] == r_rerank["retrieved"]:
            print("    FALLBACK (Gemini unavailable)")
        else:
            for rank, c in enumerate(r_rerank["retrieved"]):
                mark = "+" if c["is_match"] else "-"
                print(f"    #{rank+1} {c['doc'][:8]}.. p{c['page']}  [{mark}]  {c['score']:.4f}")

        printed += 1

    # ---- Aggregate results table ------------------------------------------
    n_total = len(dense_results)
    all_rerank_fallback = (reranker_fallback >= n_total * 0.9)

    print("\nRETRIEVAL ABLATION RESULTS")
    print("============================================================")
    print(f"{'Configuration':<28} {'CR@5':>6} {'MhS@5':>6} {'MRR':>6} {'NDCG@5':>7} {'p50':>7} {'p95':>7}")
    print("-" * 75)

    for mode in MODES:
        results = results_by_mode[mode]
        if not results:
            continue
        avg_cr  = sum(r["chunk_recall"] for r in results) / len(results)
        avg_mhs = sum(r["mh_success"]   for r in results) / len(results)
        avg_mrr = sum(r["mrr"]          for r in results) / len(results)
        avg_ndcg = sum(r["ndcg5"]       for r in results) / len(results)
        lats = sorted(r["lat"] for r in results)
        p50 = lats[len(lats)//2]
        p95 = lats[int(len(lats)*0.95)]

        label = MODE_LABELS[mode]
        if mode == "hybrid_rerank" and all_rerank_fallback:
            label += " (fallback)"
        print(f"{label:<28} {avg_cr:>6.3f} {avg_mhs:>6.3f} {avg_mrr:>6.3f} {avg_ndcg:>7.3f} {p50:>5.0f}ms {p95:>5.0f}ms")

    # ---- Per-type breakdown ----------------------------------------------
    q_types = ["lexical", "semantic", "multi_hop"]
    print("\nPER-TYPE BREAKDOWN  (ChunkRecall@5)")
    print(f"{'Type':<14} {'Dense':>7} {'BM25':>7} {'RRF(Orig)':>9} {'RRF(Decomp)':>11}")
    print("-" * 55)
    for qt in q_types:
        row = []
        for mode in ["dense", "bm25", "hybrid", "hybrid_decomp"]:
            subset = [r for r in results_by_mode[mode] if r["type"] == qt]
            val = sum(r["chunk_recall"] for r in subset) / len(subset) if subset else 0.0
            row.append(f"{val:>7.3f}" if mode != "hybrid_decomp" else f"{val:>11.3f}")
        print(f"{qt:<14} {'  '.join(row)}")

    print("\nPER-TYPE BREAKDOWN  (Multi-hop Success@5 — single-hop entries show 1.0 when CR=1.0)")
    print(f"{'Type':<14} {'Dense':>7} {'BM25':>7} {'RRF(Orig)':>9} {'RRF(Decomp)':>11}")
    print("-" * 55)
    for qt in q_types:
        row = []
        for mode in ["dense", "bm25", "hybrid", "hybrid_decomp"]:
            subset = [r for r in results_by_mode[mode] if r["type"] == qt]
            val = sum(r["mh_success"] for r in subset) / len(subset) if subset else 0.0
            row.append(f"{val:>7.3f}" if mode != "hybrid_decomp" else f"{val:>11.3f}")
        print(f"{qt:<14} {'  '.join(row)}")

    # ---- Decomposition status ---------------------------------------------
    print("\nDECOMPOSITION STATUS (V2.3)")
    print("============================================================")
    print(f"  ACTIVE   (Gemini responded): {decomp_active:>3} / {n_total}")
    print(f"  FALLBACK (quota / 429):      {decomp_fallback:>3} / {n_total}")
    print(f"  ERROR    (exception):        {decomp_error:>3} / {n_total}")

    # ---- Reranker status --------------------------------------------------
    print("\nRERANKER STATUS")
    print("============================================================")
    print(f"  ACTIVE   (Gemini responded): {reranker_active:>3} / {n_total}")
    print(f"  FALLBACK (quota / 429):      {reranker_fallback:>3} / {n_total}")
    print(f"  ERROR    (exception):        {reranker_error:>3} / {n_total}")
    if all_rerank_fallback:
        print(
            "\n  NOTE: Hybrid + Rerank results reflect FALLBACK mode (RRF output returned unchanged).\n"
            "  Reranker quality metrics cannot be evaluated until Gemini quota is restored."
        )

    # ---- Unanswerable probe ----------------------------------------------
    n_unans = len(unanswerable)
    print("\nUNANSWERABLE QUERY PROBE")
    print("============================================================")
    print(f"  Questions:          {n_unans}")
    print(f"  False-positive risk (score >= {SCORE_THRESHOLD}): {unans_fp_risk}/{n_unans}  "
          f"({100*unans_fp_risk/n_unans:.0f}%)" if n_unans else "  N/A")
    print(f"  Likely correct abstention:                 {n_unans - unans_fp_risk}/{n_unans}  "
          f"({100*(n_unans - unans_fp_risk)/n_unans:.0f}%)" if n_unans else "  N/A")
    print(
        "  (Score threshold is heuristic for dense cosine similarity;\n"
        "   true abstention testing requires the end-to-end chat pipeline.)"
    )

    # ---- Failure classification summary ----------------------------------
    total_failures = sum(failure_counts.values())
    print("\nFAILURE CLASSIFICATION  (RRF misses, dense+BM25 as oracle)")
    print("============================================================")
    print(f"  SEM_MISS  (Dense missed, BM25 retrieved): {failure_counts['SEM_MISS']}")
    print(f"  LEX_MISS  (BM25 missed, Dense retrieved): {failure_counts['LEX_MISS']}")
    print(f"  RRF_DEMOTE (Both retrieved, RRF demoted): {failure_counts['RRF_DEMOTE']}")
    print(f"  BOTH_MISS  (Neither retriever found GT):  {failure_counts['BOTH_MISS']}")
    print(f"  Total RRF failures:                       {total_failures}")

def run_e2e_evaluation(api_url: str, token: str, qa_data: list, active_docs: list):
    print("\nEND-TO-END EVALUATION")
    print("============================================================")
    
    doc_name_to_id = {d["filename"]: d["document_id"] for d in active_docs}
    
    metrics = {
        "Answer Accuracy": [],
        "Faithfulness": [],
        "Answer Relevancy": [],
        "Citation Precision": [],
        "Citation Recall": [],
        "Correct Abstention Rate": [],
        "False Positive Rate": [],
        "Latency": [],
        "retrieval_latency": [],
        "reranking_latency": [],
        "llm_latency": []
    }
    
    telemetry = {
        "queries": 0,
        "llm_success": 0,
        "llm_reranker_fallback": 0,
        "api_errors": 0,
    }
    
    diagnostic_failures = []

    for item in qa_data:
        qid = item["id"]
        q = item["question"]
        is_ans = item.get("is_answerable", True)
        src_doc = item.get("source_document")
        rel_doc_id = doc_name_to_id.get(src_doc)
        
        t0 = time.perf_counter()
        try:
            resp = _ask(api_url, token, q, mode="full")
        except Exception as e:
            print(f"Error on {qid}: {e}")
            continue
            
        latency = (time.perf_counter() - t0) * 1000
        metrics["Latency"].append(latency)
        
        trace = resp.get("trace", {})
        metrics["retrieval_latency"].append(trace.get("embedding_ms", 0) + trace.get("dense_ms", 0) + trace.get("bm25_ms", 0))
        metrics["reranking_latency"].append(trace.get("rerank_ms", 0))
        metrics["llm_latency"].append(trace.get("llm_ms", 0))
        
        telemetry["queries"] += 1
        
        reranker = trace.get("reranker")
        if reranker:
            if reranker.get("fallback"):
                telemetry["llm_reranker_fallback"] += 1
            if reranker.get("status") == "error":
                telemetry["api_errors"] += 1
                
        generation = trace.get("generation")
        if generation:
            if generation.get("status") == "success":
                telemetry["llm_success"] += 1
            if generation.get("status") == "error":
                telemetry["api_errors"] += 1
        
        answer = resp.get("answer", "")
        abstained = resp.get("abstained", False)
        citations = resp.get("citations", [])
        retrieved_docs = list({c.get("document_id", "") for c in citations})
        
        if is_ans:
            # We expect an answer and retrieved docs
            if rel_doc_id and rel_doc_id not in retrieved_docs:
                retrieved_files = []
                for c in citations:
                    filename = c.get('metadata', {}).get('filename', 'Unknown')
                    page = c.get('metadata', {}).get('page_number', '1')
                    score = c.get('score', 0)
                    retrieved_files.append(f"{filename} p{page} score={score:.2f}")
                diagnostic_failures.append({
                    "id": qid,
                    "question": q,
                    "expected": src_doc,
                    "retrieved": retrieved_files
                })
            
            if abstained:
                metrics["Answer Accuracy"].append(0.0)
                # If abstained, faithfulness and relevancy are N/E (None)
                metrics["Faithfulness"].append(None)
                metrics["Answer Relevancy"].append(None)
            else:
                expected_keywords = item.get("expected_answer_keywords", [])
                answer_lower = answer.lower()
                keyword_hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
                answer_correct = 1.0 if (expected_keywords and keyword_hits / len(expected_keywords) >= 0.5) else 0.0
                metrics["Answer Accuracy"].append(answer_correct)
                
                context = " ".join(c.get("chunk_preview", "") for c in citations)
                faith = evaluate_faithfulness(q, answer, context).get("score", 0.0)
                relev = evaluate_answer_relevancy(q, answer).get("score", 0.0)
                metrics["Faithfulness"].append(faith)
                metrics["Answer Relevancy"].append(relev)
                
            if rel_doc_id:
                # Mock chunk IDs for citation precision/recall based on document_id matching
                # Since we don't know the exact ground truth chunk IDs, we use doc level
                cited_docs = [c["document_id"] for c in citations]
                cit_prec = 1.0 if all(d == rel_doc_id for d in cited_docs) and cited_docs else 0.0
                cit_rec = 1.0 if rel_doc_id in cited_docs else 0.0
                metrics["Citation Precision"].append(cit_prec)
                metrics["Citation Recall"].append(cit_rec)
        else:
            # Unanswerable
            if abstained:
                metrics["Correct Abstention Rate"].append(1.0)
                metrics["False Positive Rate"].append(0.0)
            else:
                metrics["Correct Abstention Rate"].append(0.0)
                metrics["False Positive Rate"].append(1.0)
                
    # Aggregate
    def get_avg(key):
        vals = [v for v in metrics[key] if v is not None]
        return sum(vals)/len(vals) if vals else "N/E"
        
    print(f"{'Metric':<30} {'Result':<10}")
    print("-" * 60)
    for m in ["Answer Accuracy", "Faithfulness", "Answer Relevancy", "Citation Precision", "Citation Recall", "Correct Abstention Rate", "False Positive Rate"]:
        val = get_avg(m)
        if val == "N/E":
            print(f"{m:<30} N/E")
        else:
            print(f"{m:<30} {val:.2f}")
            
    print("\nSYSTEM RELIABILITY")
    print("============================================================")
    queries = max(telemetry["queries"], 1)
    print(f"LLM Success Rate               {telemetry['llm_success']/queries*100:>5.1f}%")
    print(f"LLM Reranker Fallback          {telemetry['llm_reranker_fallback']/queries*100:>5.1f}%")
    print(f"API Error Rate                 {telemetry['api_errors']/queries*100:>5.1f}%")
            
    print("\nPERFORMANCE")
    print("============================================================")
    print(f"{'Pipeline Stage':<25} {'p50':<10} {'p95':<10}")
    print("-" * 60)
    
    stages = [
        ("Retrieval (Dense+BM25)", "retrieval_latency"),
        ("Reranking", "reranking_latency"),
        ("Gemini Generation", "llm_latency"),
        ("Total", "Latency")
    ]
    
    for label, key in stages:
        vals = sorted(metrics[key])
        if vals:
            p50 = vals[len(vals)//2]
            p95 = vals[int(len(vals)*0.95)]
            print(f"{label:<25} {p50:>5.0f}ms {p95:>5.0f}ms")
        else:
            print(f"{label:<25} N/A    N/A")
            
    if diagnostic_failures:
        print("\nRETRIEVAL FAILURES DIAGNOSTICS")
        print("============================================================")
        for df in diagnostic_failures:
            print(f"QA ID: {df['id']}")
            print(f"Question: {df['question']}")
            print(f"Expected source: {df['expected']}")
            print(f"Retrieved:")
            for i, r in enumerate(df['retrieved'], 1):
                print(f"{i}. {r}")
            print(f"Failure: RETRIEVAL_FAILURE\n")
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--ablation", action="store_true")
    parser.add_argument("--bootstrap", action="store_true")
    args = parser.parse_args()
    
    if args.bootstrap:
        from evaluation.bootstrap import bootstrap
        bootstrap(args.api_url)
        
    if args.ablation:
        preflight_data = run_preflight(args.api_url, args.token)
        run_retrieval_ablation(args.api_url, args.token, preflight_data["qa_data"], preflight_data["active_docs"])
        # run_e2e_evaluation(args.api_url, args.token, preflight_data["qa_data"], preflight_data["active_docs"])
        sys.exit(0)
    else:
        print("Please provide --ablation flag.")
