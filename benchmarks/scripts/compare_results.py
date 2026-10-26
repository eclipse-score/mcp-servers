#!/usr/bin/env python3
# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

"""Compare results with and without graph."""

import json
import sys
from pathlib import Path


def calculate_improvement(graph_score: float, nograph_score: float) -> float:
    """Calculate percentage improvement."""
    if nograph_score == 0:
        return 0.0
    return ((graph_score - nograph_score) / nograph_score) * 100


def main() -> int:
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "results"
    
    if not results_dir.exists():
        print("No results found. Run benchmarks first: uv run python benchmarks/scripts/run_eval.py --all")
        return 1
    
    print("=" * 80)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 80)
    
    all_results = {
        "graph": {"time": [], "tokens": [], "correctness": []},
        "nograph": {"time": [], "tokens": [], "correctness": []},
    }
    
    for repo_dir in sorted(results_dir.iterdir()):
        if not repo_dir.is_dir():
            continue
        
        print(f"\n{repo_dir.name.upper()}")
        print("-" * 80)
        print(f"{'Question':<30} {'Mode':<10} {'Correct':<10} {'Time':<10} {'Tokens':<10}")
        print("-" * 80)
        
        # Find all graph results
        for graph_result_path in sorted(repo_dir.glob("*_graph.json")):
            question_id = graph_result_path.stem.replace("_graph", "")
            nograph_result_path = graph_result_path.parent / f"{question_id}_nograph.json"
            
            if not nograph_result_path.exists():
                continue
            
            with open(graph_result_path) as f:
                graph_result = json.load(f)
            
            with open(nograph_result_path) as f:
                nograph_result = json.load(f)
            
            # Print results
            print(f"{question_id:<30} {'graph':<10} "
                  f"{graph_result['metrics']['correctness_score']:<10.2f} "
                  f"{graph_result['metrics']['time_ms']:<10} "
                  f"{graph_result['metrics']['tokens_used']:<10}")
            
            print(f"{'':<30} {'nograph':<10} "
                  f"{nograph_result['metrics']['correctness_score']:<10.2f} "
                  f"{nograph_result['metrics']['time_ms']:<10} "
                  f"{nograph_result['metrics']['tokens_used']:<10}")
            
            # Calculate improvement
            improvement = calculate_improvement(
                graph_result['metrics']['correctness_score'],
                nograph_result['metrics']['correctness_score']
            )
            print(f"{'':<30} {'improve':<10} {improvement:>+.1f}%")
            print()
            
            # Aggregate
            for mode, result in [("graph", graph_result), ("nograph", nograph_result)]:
                all_results[mode]["time"].append(result["metrics"]["time_ms"])
                all_results[mode]["tokens"].append(result["metrics"]["tokens_used"])
                all_results[mode]["correctness"].append(result["metrics"]["correctness_score"])
    
    # Overall summary
    if all_results["graph"]["correctness"]:
        print("\n" + "=" * 80)
        print("OVERALL SUMMARY")
        print("=" * 80)
        
        n = len(all_results["graph"]["correctness"])
        
        avg_graph_correctness = sum(all_results["graph"]["correctness"]) / n
        avg_nograph_correctness = sum(all_results["nograph"]["correctness"]) / n
        avg_graph_time = sum(all_results["graph"]["time"]) / n
        avg_nograph_time = sum(all_results["nograph"]["time"]) / n
        avg_graph_tokens = sum(all_results["graph"]["tokens"]) / n
        avg_nograph_tokens = sum(all_results["nograph"]["tokens"]) / n
        
        print(f"\nAverage Correctness:")
        print(f"  Graph:   {avg_graph_correctness:.2f}")
        print(f"  NoGraph: {avg_nograph_correctness:.2f}")
        print(f"  Improvement: +{calculate_improvement(avg_graph_correctness, avg_nograph_correctness):.1f}%")
        
        print(f"\nAverage Time (ms):")
        print(f"  Graph:   {avg_graph_time:.0f}")
        print(f"  NoGraph: {avg_nograph_time:.0f}")
        
        print(f"\nAverage Tokens:")
        print(f"  Graph:   {avg_graph_tokens:.0f}")
        print(f"  NoGraph: {avg_nograph_tokens:.0f}")
        print(f"  Token Change: {((avg_graph_tokens - avg_nograph_tokens) / avg_nograph_tokens * 100):+.1f}%")
        
        print("\n" + "=" * 80)
        print("SUCCESS CRITERIA")
        print("=" * 80)
        
        improvement_pct = calculate_improvement(avg_graph_correctness, avg_nograph_correctness)
        
        criteria = [
            ("✅" if improvement_pct >= 20 else "❌", f"Correctness improvement >= 20%: {improvement_pct:.1f}%"),
            ("✅" if avg_graph_time < 5000 else "❌", f"Average query time < 5000ms: {avg_graph_time:.0f}ms"),
            ("✅" if avg_graph_tokens < avg_nograph_tokens * 1.3 else "❌", f"Token overhead < 30%: {((avg_graph_tokens - avg_nograph_tokens) / avg_nograph_tokens * 100):+.1f}%"),
        ]
        
        for mark, desc in criteria:
            print(f"{mark} {desc}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
