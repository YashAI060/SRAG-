import json
import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from evaluation.evaluate import run_evaluation

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    parser.add_argument("--url", default="http://localhost:8000/api/v1")
    parser.add_argument("--dataset", default="evaluation/datasets/qa_dataset.json")
    args = parser.parse_args()

    modes = ["dense", "bm25", "hybrid", "hybrid_rerank", "full"]
    
    print("\n# Ablation Benchmark Results\n")
    print("| Configuration | Recall@5 | MRR | Faithfulness | Latency |")
    print("|---------------|----------|-----|--------------|---------|")
    
    for mode in modes:
        res = run_evaluation(args.url, args.token, args.dataset, mode=mode)
        
        # Display name mapping
        name_map = {
            "dense": "Dense",
            "bm25": "BM25",
            "hybrid": "Hybrid + RRF",
            "hybrid_rerank": "Hybrid + Reranker",
            "full": "Full Pipeline"
        }
        
        name = name_map[mode]
        recall = res.get("recall_at_5", 0.0)
        mrr = res.get("mrr", 0.0)
        faith = res.get("faithfulness", 0.0)
        lat = res.get("avg_latency_ms", 0.0)
        
        print(f"| {name} | {recall:.2f} | {mrr:.2f} | {faith:.2f} | {lat:.0f}ms |")

if __name__ == "__main__":
    main()
