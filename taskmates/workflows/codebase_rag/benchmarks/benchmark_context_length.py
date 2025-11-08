"""
Benchmark script to measure the effect of context length on crashes.

Tests if longer prompts cause more Ollama crashes.
"""
import time
from typing import Dict, Any
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


def call_ollama_with_context(base_prompt: str, context_tokens: int, model_name: str = DEFAULT_MODEL_NAME) -> Dict[str, Any]:
    """Make an Ollama call with a specific context length."""
    # Approximate: 1 token ~= 4 characters
    padding = "x" * (context_tokens * 4)
    full_prompt = f"{base_prompt}\n\nContext: {padding}"
    
    llm = ChatOllama(model=model_name)
    
    start = time.time()
    crashed = False
    retries = 0
    
    while retries < 3:
        try:
            response = llm.invoke([HumanMessage(content=full_prompt)])
            elapsed = time.time() - start
            return {
                "success": True,
                "elapsed": elapsed,
                "crashed": crashed,
                "retries": retries,
                "context_tokens": context_tokens
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
                    "context_tokens": context_tokens,
                    "error": str(e)
                }
            time.sleep(1.0 * (2 ** retries))


def main():
    """Run context length benchmarks."""
    model_name = DEFAULT_MODEL_NAME
    base_prompt = "Summarize the following context in one sentence."
    
    # Warm up Ollama first
    warmup_ollama(model_name)
    
    # Test different context lengths (in tokens)
    context_lengths = [100, 1000, 3000, 5000, 7000, 10000]
    
    print("=" * 60)
    print("BENCHMARK: Context Length Effect on Crashes")
    print("=" * 60)
    print(f"Model: {model_name}")
    print(f"Testing context lengths: {context_lengths}")
    print()
    
    results = []
    
    for context_tokens in context_lengths:
        print(f"Testing {context_tokens} tokens...", end=" ", flush=True)
        result = call_ollama_with_context(base_prompt, context_tokens, model_name)
        results.append(result)
        
        status = "✓" if result["success"] else "✗"
        print(f"{status} {result['elapsed']:.2f}s, "
              f"crashed: {result['crashed']}, retries: {result['retries']}")
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_crashes = sum(1 for r in results if r["crashed"])
    total_retries = sum(r["retries"] for r in results)
    
    print(f"Total tests: {len(results)}")
    print(f"Total crashes: {total_crashes}")
    print(f"Total retries: {total_retries}")
    print()
    
    print("Context Length vs Crashes:")
    for result in results:
        crash_indicator = "CRASH" if result["crashed"] else "OK"
        print(f"  {result['context_tokens']:5d} tokens: {crash_indicator:5s} "
              f"(retries: {result['retries']}, time: {result['elapsed']:.2f}s)")
    
    # Save detailed results
    with open("benchmark_context_length_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print()
    print("Detailed results saved to: benchmark_context_length_results.json")


if __name__ == "__main__":
    main()
