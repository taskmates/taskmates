"""
Benchmark script to measure the effect of parallelism on response time and crashes.

Tests:
1. Sequential vs parallel execution (response time)
2. Number of crashes at different parallelism levels
"""
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import json

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from taskmates.workflows.codebase_rag.constants import DEFAULT_MODEL_NAME


def warmup_ollama(model_name: str = DEFAULT_MODEL_NAME):
    """Warm up Ollama by loading the model."""
    print("Warming up Ollama (loading model)...")
    llm = ChatOllama(model=model_name)
    llm.invoke([HumanMessage(content="Hi")])
    print("Warmup complete.\n")


def call_ollama(prompt: str, model_name: str = DEFAULT_MODEL_NAME) -> Dict[str, Any]:
    """Make a single Ollama call and track if it crashed."""
    llm = ChatOllama(model=model_name)
    
    start = time.time()
    crashed = False
    retries = 0
    
    while retries < 3:
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            elapsed = time.time() - start
            return {
                "success": True,
                "elapsed": elapsed,
                "crashed": crashed,
                "retries": retries
            }
        except Exception as e:
            crashed = True
            retries += 1
            if retries >= 3:
                return {
                    "success": False,
                    "elapsed": time.time() - start,
                    "crashed": True,
                    "retries": retries,
                    "error": str(e)
                }
            time.sleep(1.0 * (2 ** retries))


def run_sequential(prompts: List[str], model_name: str) -> Dict[str, Any]:
    """Run prompts sequentially."""
    start = time.time()
    results = []
    
    for i, prompt in enumerate(prompts):
        print(f"  Sequential {i+1}/{len(prompts)}...", end=" ", flush=True)
        result = call_ollama(prompt, model_name)
        results.append(result)
        status = "✓" if result["success"] else "✗"
        print(f"{status} {result['elapsed']:.2f}s")
    
    total_time = time.time() - start
    
    return {
        "mode": "sequential",
        "total_time": total_time,
        "num_prompts": len(prompts),
        "results": results,
        "total_crashes": sum(1 for r in results if r["crashed"]),
        "total_retries": sum(r["retries"] for r in results)
    }


def run_parallel(prompts: List[str], model_name: str, max_workers: int) -> Dict[str, Any]:
    """Run prompts in parallel."""
    start = time.time()
    
    print(f"  Parallel ({max_workers} workers)...", flush=True)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(call_ollama, prompt, model_name) for prompt in prompts]
        results = [f.result() for f in futures]
    
    total_time = time.time() - start
    
    for i, result in enumerate(results):
        status = "✓" if result["success"] else "✗"
        print(f"    {i+1}/{len(prompts)}: {status} {result['elapsed']:.2f}s")
    
    return {
        "mode": f"parallel_{max_workers}",
        "total_time": total_time,
        "num_prompts": len(prompts),
        "results": results,
        "total_crashes": sum(1 for r in results if r["crashed"]),
        "total_retries": sum(r["retries"] for r in results)
    }


def main():
    """Run benchmarks."""
    model_name = DEFAULT_MODEL_NAME
    
    # Warm up Ollama first
    warmup_ollama(model_name)
    
    # Create test prompts: short, medium, large
    short_prompt = "What is Python?"
    
    medium_prompt = "Explain Python decorators in detail, including how they work, common use cases, and best practices."
    
    # Large prompt: ~7000 tokens (28000 characters)
    large_context = "x" * 28000
    large_prompt = f"Summarize this context: {large_context}"
    
    prompts = [short_prompt, medium_prompt, large_prompt]
    
    print("=" * 60)
    print("BENCHMARK: Parallelism Effect on Response Time and Crashes")
    print("=" * 60)
    print(f"Model: {model_name}")
    print(f"Number of prompts: {len(prompts)}")
    print(f"Prompt sizes: short, medium, large (~7000 tokens)")
    print()
    
    # Test 1: Sequential
    print("Running sequential...")
    seq_result = run_sequential(prompts, model_name)
    print(f"Sequential total: {seq_result['total_time']:.2f}s, "
          f"crashes: {seq_result['total_crashes']}, "
          f"retries: {seq_result['total_retries']}\n")
    
    # Test 2: Parallel with 2 workers
    print("Running parallel (2 workers)...")
    par2_result = run_parallel(prompts, model_name, max_workers=2)
    print(f"Parallel (2) total: {par2_result['total_time']:.2f}s, "
          f"crashes: {par2_result['total_crashes']}, "
          f"retries: {par2_result['total_retries']}\n")
    
    # Test 3: Parallel with 3 workers
    print("Running parallel (3 workers)...")
    par3_result = run_parallel(prompts, model_name, max_workers=3)
    print(f"Parallel (3) total: {par3_result['total_time']:.2f}s, "
          f"crashes: {par3_result['total_crashes']}, "
          f"retries: {par3_result['total_retries']}\n")
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    results = [seq_result, par2_result, par3_result]
    
    for result in results:
        speedup = seq_result['total_time'] / result['total_time']
        print(f"{result['mode']:15s}: {result['total_time']:6.2f}s "
              f"(speedup: {speedup:.2f}x, crashes: {result['total_crashes']}, "
              f"retries: {result['total_retries']})")
    
    # Save detailed results
    with open("benchmark_parallelism_results.json", "w") as f:
        json.dump({
            "sequential": seq_result,
            "parallel_2": par2_result,
            "parallel_3": par3_result
        }, f, indent=2)
    
    print()
    print("Detailed results saved to: benchmark_parallelism_results.json")


if __name__ == "__main__":
    main()
