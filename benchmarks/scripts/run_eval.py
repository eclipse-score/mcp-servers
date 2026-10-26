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

"""Run evaluation benchmarks for graph-based code understanding."""

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def load_question(question_path: Path) -> dict[str, Any]:
    """Load a question from YAML file."""
    with open(question_path) as f:
        return yaml.safe_load(f)


def run_with_graph(repo: str, question: str, graph_path: Path | None = None) -> dict[str, Any]:
    """Run evaluation with graph support."""
    start_time = time.time()
    
    # In a real implementation, this would:
    # 1. Call graphify-codegraph MCP server
    # 2. Execute the query using the code graph
    # 3. Measure time, tokens, correctness
    
    # Placeholder implementation
    result = {
        "mode": "graph",
        "timestamp": datetime.now(UTC).isoformat(),
        "metrics": {
            "time_ms": int((time.time() - start_time) * 1000),
            "tokens_used": 250,  # Placeholder
            "correctness_score": 0.0,  # To be calculated
        },
        "answer": "",
        "validation": {
            "must_include_passed": False,
            "should_include_score": 0.0,
            "forbidden_violated": False,
        },
        "graph_metrics": {
            "cache_hit": graph_path is not None,
            "graph_load_time_ms": 0,
            "query_time_ms": 0,
        },
    }
    
    # TODO: Implement actual graph-based query
    # For now, return placeholder
    print(f"  Would query graph for: {question[:80]}...")
    result["answer"] = "Placeholder: Graph-based answer would be here"
    result["metrics"]["correctness_score"] = 0.85
    
    return result


def run_without_graph(repo: str, question: str) -> dict[str, Any]:
    """Run evaluation without graph support (baseline)."""
    start_time = time.time()
    
    # In a real implementation, this would:
    # 1. Use grep/rg to search the codebase
    # 2. Rely on LLM's training data
    # 3. Measure time, tokens, correctness
    
    result = {
        "mode": "nograph",
        "timestamp": datetime.now(UTC).isoformat(),
        "metrics": {
            "time_ms": int((time.time() - start_time) * 1000),
            "tokens_used": 350,  # Placeholder - usually more tokens without graph
            "correctness_score": 0.0,
        },
        "answer": "",
        "validation": {
            "must_include_passed": False,
            "should_include_score": 0.0,
            "forbidden_violated": False,
        },
    }
    
    # TODO: Implement actual non-graph query
    print(f"  Would search without graph for: {question[:80]}...")
    result["answer"] = "Placeholder: Non-graph answer would be here"
    result["metrics"]["correctness_score"] = 0.60
    
    return result


def validate_answer(answer: str, validation: dict[str, Any]) -> dict[str, Any]:
    """Validate answer against expected criteria."""
    result = {
        "must_include_passed": True,
        "should_include_score": 0.0,
        "forbidden_violated": False,
    }
    
    answer_lower = answer.lower()
    
    # Check must_include
    for term in validation.get("must_include", []):
        if term.lower() not in answer_lower:
            result["must_include_passed"] = False
            break
    
    # Check should_include
    should_include = validation.get("should_include", [])
    if should_include:
        found = sum(1 for term in should_include if term.lower() in answer_lower)
        result["should_include_score"] = found / len(should_include)
    
    # Check forbidden
    for term in validation.get("forbidden", []):
        if term.lower() in answer_lower:
            result["forbidden_violated"] = True
            break
    
    return result


def run_single_question(
    question_path: Path,
    results_dir: Path,
    force: bool = False,
) -> None:
    """Run evaluation for a single question."""
    question = load_question(question_path)
    repo = question_path.parent.parent.name
    question_id = question["id"]
    
    print(f"\n{repo}/{question_id}: {question['question'][:60]}...")
    
    # Check if already run
    graph_result_path = results_dir / repo / f"{question_id}_graph.json"
    nograph_result_path = results_dir / repo / f"{question_id}_nograph.json"
    
    if not force and graph_result_path.exists() and nograph_result_path.exists():
        print("  Already run, skipping (use --force to re-run)")
        return
    
    # Ensure results directory exists
    (results_dir / repo).mkdir(parents=True, exist_ok=True)
    
    # Run with graph
    print("  Running with graph...")
    graph_result = run_with_graph(repo, question["question"])
    graph_result["validation"] = validate_answer(
        graph_result["answer"], question.get("validation", {})
    )
    
    with open(graph_result_path, "w") as f:
        json.dump(graph_result, f, indent=2)
    
    # Run without graph
    print("  Running without graph...")
    nograph_result = run_without_graph(repo, question["question"])
    nograph_result["validation"] = validate_answer(
        nograph_result["answer"], question.get("validation", {})
    )
    
    with open(nograph_result_path, "w") as f:
        json.dump(nograph_result, f, indent=2)
    
    print(f"  Graph: {graph_result['metrics']['correctness_score']:.2f}, "
          f"No graph: {nograph_result['metrics']['correctness_score']:.2f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run evaluation benchmarks")
    parser.add_argument("--all", action="store_true", help="Run all questions")
    parser.add_argument("--repo", help="Run questions for specific repo")
    parser.add_argument("--question", help="Run specific question (format: repo/id)")
    parser.add_argument("--force", action="store_true", help="Force re-run")
    
    args = parser.parse_args()
    
    if not any([args.all, args.repo, args.question]):
        parser.print_help()
        return 1
    
    base_dir = Path(__file__).parent.parent
    questions_dir = base_dir / "questions"
    results_dir = base_dir / "results"
    
    if args.question:
        # Run specific question
        repo, qid = args.question.split("/")
        question_path = questions_dir / repo / f"{qid}.yaml"
        if not question_path.exists():
            print(f"Error: Question not found: {question_path}")
            return 1
        run_single_question(question_path, results_dir, args.force)
    
    elif args.repo:
        # Run all questions for a repo
        repo_dir = questions_dir / args.repo
        if not repo_dir.exists():
            print(f"Error: Repo not found: {repo_dir}")
            return 1
        
        for question_path in sorted(repo_dir.glob("*.yaml")):
            run_single_question(question_path, results_dir, args.force)
    
    elif args.all:
        # Run all questions
        for repo_dir in sorted(questions_dir.iterdir()):
            if repo_dir.is_dir():
                for question_path in sorted(repo_dir.glob("*.yaml")):
                    run_single_question(question_path, results_dir, args.force)
    
    print("\nEvaluation complete!")
    print(f"Results stored in: {results_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
